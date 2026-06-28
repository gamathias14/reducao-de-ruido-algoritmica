/**
 * Receptor de respostas para a pagina GitHub Pages do questionario extensionista.
 *
 * Uso:
 * 1. Abra https://script.google.com/ e crie um projeto.
 * 2. Cole este arquivo em Code.gs.
 * 3. Execute setupQuestionarioReceiver() uma vez para criar/validar a planilha.
 * 4. Publique como Web App:
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 5. Copie a URL do Web App para submission.endpoint em docs/questionario/questionario.config.js
 *    e altere submission.enabled para true.
 *
 * O endpoint aceita schemas variaveis: respostas antigas continuam preservadas
 * como JSON bruto e a aba responses_wide ganha novas colunas quando perguntas
 * forem adicionadas.
 */

const RECEIVER_CONFIG = {
  spreadsheetId: "10HsBn2HnTyv9eKbhEqv6zQOy6jDjLc-uroqs-ElWdmc",
  spreadsheetName: "Respostas - Questionario Extensionista PTC3527",
  maxPayloadBytes: 220000,
  rawSheetName: "responses_raw",
  wideSheetName: "responses_wide",
  schemaSheetName: "schema_history",
  auditSheetName: "audit",
  errorSheetName: "errors",
};

function setupQuestionarioReceiver() {
  const spreadsheet = getOrCreateSpreadsheet_();
  ensureSheets_(spreadsheet);
  Logger.log("Spreadsheet URL: " + spreadsheet.getUrl());
  Logger.log("Spreadsheet ID: " + spreadsheet.getId());
  return spreadsheet.getUrl();
}

function doGet() {
  return json_({
    ok: true,
    service: "ptc3527-questionario-receiver",
    message: "Endpoint ativo. Use POST para registrar respostas.",
    timestamp: new Date().toISOString(),
  });
}

function doPost(event) {
  const receivedAt = new Date();
  let payloadText = "";

  try {
    payloadText = event && event.postData && event.postData.contents ? event.postData.contents : "";
    if (!payloadText) {
      throw new Error("Payload vazio.");
    }
    if (payloadText.length > RECEIVER_CONFIG.maxPayloadBytes) {
      throw new Error("Payload acima do limite configurado.");
    }

    const payload = JSON.parse(payloadText);
    validatePayload_(payload);

    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      const spreadsheet = getOrCreateSpreadsheet_();
      ensureSheets_(spreadsheet);
      appendRawResponse_(spreadsheet, payload, payloadText, receivedAt);
      appendWideResponse_(spreadsheet, payload, receivedAt);
      appendSchemaIfNeeded_(spreadsheet, payload, receivedAt);
      appendAudit_(spreadsheet, "response_received", payload.responseId, {
        questionnaireId: payload.questionnaireId,
        schemaVersion: payload.schemaVersion,
        formDefinitionHash: payload.formDefinitionHash,
        audioManifestHash: payload.audioManifestHash,
      }, receivedAt);
    } finally {
      lock.releaseLock();
    }

    return json_({
      ok: true,
      responseId: payload.responseId,
      receivedAt: receivedAt.toISOString(),
    });
  } catch (error) {
    recordError_(error, payloadText, receivedAt);
    return json_({
      ok: false,
      error: String(error && error.message ? error.message : error),
      receivedAt: receivedAt.toISOString(),
    });
  }
}

function validatePayload_(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("Payload invalido.");
  }
  if (!payload.responseId) {
    throw new Error("responseId ausente.");
  }
  if (!payload.questionnaireId) {
    throw new Error("questionnaireId ausente.");
  }
  if (!payload.schemaVersion) {
    throw new Error("schemaVersion ausente.");
  }
  if (!payload.answers || typeof payload.answers !== "object") {
    throw new Error("answers ausente ou invalido.");
  }
}

function getOrCreateSpreadsheet_() {
  if (RECEIVER_CONFIG.spreadsheetId) {
    return SpreadsheetApp.openById(RECEIVER_CONFIG.spreadsheetId);
  }

  const properties = PropertiesService.getScriptProperties();
  const existingId = properties.getProperty("QUESTIONARIO_SPREADSHEET_ID");
  if (existingId) {
    return SpreadsheetApp.openById(existingId);
  }

  const spreadsheet = SpreadsheetApp.create(RECEIVER_CONFIG.spreadsheetName);
  properties.setProperty("QUESTIONARIO_SPREADSHEET_ID", spreadsheet.getId());
  return spreadsheet;
}

function ensureSheets_(spreadsheet) {
  ensureSheetWithHeaders_(spreadsheet, RECEIVER_CONFIG.rawSheetName, rawHeaders_());
  ensureSheetWithHeaders_(spreadsheet, RECEIVER_CONFIG.wideSheetName, wideBaseHeaders_());
  ensureSheetWithHeaders_(spreadsheet, RECEIVER_CONFIG.schemaSheetName, schemaHeaders_());
  ensureSheetWithHeaders_(spreadsheet, RECEIVER_CONFIG.auditSheetName, auditHeaders_());
  ensureSheetWithHeaders_(spreadsheet, RECEIVER_CONFIG.errorSheetName, errorHeaders_());
}

function ensureSheetWithHeaders_(spreadsheet, sheetName, headers) {
  let sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(sheetName);
  }

  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
  }

  const currentHeaders = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), headers.length)).getValues()[0];
  const missing = headers.filter(function(header) {
    return currentHeaders.indexOf(header) === -1;
  });
  if (missing.length) {
    sheet.getRange(1, currentHeaders.length + 1, 1, missing.length).setValues([missing]);
  }
  return sheet;
}

function appendRawResponse_(spreadsheet, payload, payloadText, receivedAt) {
  const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.rawSheetName);
  const row = [
    receivedAt.toISOString(),
    payload.responseId || "",
    payload.questionnaireId || "",
    payload.schemaVersion || "",
    payload.formDefinitionHash || "",
    payload.audioManifestHash || "",
    payload.elapsedMs || "",
    payload.page && payload.page.href ? payload.page.href : "",
    payload.page && payload.page.userAgent ? payload.page.userAgent : "",
    payload.page && payload.page.language ? payload.page.language : "",
    payload.page && payload.page.timeZone ? payload.page.timeZone : "",
    JSON.stringify(payload.audioOrder || []),
    JSON.stringify(payload.localExperiment || {}),
    JSON.stringify(payload.answers || {}),
    JSON.stringify(payload.questionSnapshot || []),
    payloadText,
  ];
  sheet.appendRow(row);
}

function appendWideResponse_(spreadsheet, payload, receivedAt) {
  const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.wideSheetName);
  const answerIds = Object.keys(payload.answers || {});
  const headers = ensureWideHeaders_(sheet, answerIds);
  const rowObject = {
    received_at: receivedAt.toISOString(),
    response_id: payload.responseId || "",
    questionnaire_id: payload.questionnaireId || "",
    schema_version: payload.schemaVersion || "",
    form_definition_hash: payload.formDefinitionHash || "",
    audio_manifest_hash: payload.audioManifestHash || "",
    elapsed_ms: payload.elapsedMs || "",
    page_href: payload.page && payload.page.href ? payload.page.href : "",
  };

  answerIds.forEach(function(answerId) {
    rowObject[answerId] = normalizeAnswer_(payload.answers[answerId]);
  });

  sheet.appendRow(headers.map(function(header) {
    return rowObject[header] !== undefined ? rowObject[header] : "";
  }));
}

function ensureWideHeaders_(sheet, answerIds) {
  const base = wideBaseHeaders_();
  const existing = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), base.length)).getValues()[0].filter(String);
  const headers = existing.length ? existing : base.slice();
  answerIds.forEach(function(answerId) {
    if (headers.indexOf(answerId) === -1) {
      headers.push(answerId);
    }
  });
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  return headers;
}

function appendSchemaIfNeeded_(spreadsheet, payload, receivedAt) {
  const key = [
    "schema",
    payload.questionnaireId || "",
    payload.schemaVersion || "",
    payload.formDefinitionHash || "",
    payload.audioManifestHash || "",
  ].join(":");

  const properties = PropertiesService.getScriptProperties();
  if (properties.getProperty(key)) {
    return;
  }

  const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.schemaSheetName);
  sheet.appendRow([
    receivedAt.toISOString(),
    key,
    payload.questionnaireId || "",
    payload.schemaVersion || "",
    payload.formDefinitionHash || "",
    payload.audioManifestHash || "",
    JSON.stringify(payload.questionSnapshot || []),
    JSON.stringify(payload.audioOrder || []),
  ]);
  properties.setProperty(key, "1");
}

function appendAudit_(spreadsheet, eventName, responseId, details, receivedAt) {
  const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.auditSheetName);
  sheet.appendRow([
    receivedAt.toISOString(),
    eventName,
    responseId || "",
    JSON.stringify(details || {}),
  ]);
}

function recordError_(error, payloadText, receivedAt) {
  try {
    const spreadsheet = getOrCreateSpreadsheet_();
    ensureSheets_(spreadsheet);
    const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.errorSheetName);
    sheet.appendRow([
      receivedAt.toISOString(),
      String(error && error.message ? error.message : error),
      payloadText ? payloadText.substring(0, 2000) : "",
    ]);
  } catch (nestedError) {
    Logger.log("Erro ao registrar falha: " + nestedError);
  }
}

function normalizeAnswer_(answer) {
  if (!answer) {
    return "";
  }
  if (answer.displayValue !== undefined && answer.displayValue !== null) {
    return String(answer.displayValue);
  }
  if (Array.isArray(answer.value)) {
    return answer.value.join("; ");
  }
  if (answer.value !== undefined && answer.value !== null) {
    return String(answer.value);
  }
  return JSON.stringify(answer);
}

function rawHeaders_() {
  return [
    "received_at",
    "response_id",
    "questionnaire_id",
    "schema_version",
    "form_definition_hash",
    "audio_manifest_hash",
    "elapsed_ms",
    "page_href",
    "user_agent",
    "language",
    "time_zone",
    "audio_order_json",
    "local_experiment_json",
    "answers_json",
    "question_snapshot_json",
    "payload_json",
  ];
}

function wideBaseHeaders_() {
  return [
    "received_at",
    "response_id",
    "questionnaire_id",
    "schema_version",
    "form_definition_hash",
    "audio_manifest_hash",
    "elapsed_ms",
    "page_href",
  ];
}

function schemaHeaders_() {
  return [
    "recorded_at",
    "schema_key",
    "questionnaire_id",
    "schema_version",
    "form_definition_hash",
    "audio_manifest_hash",
    "question_snapshot_json",
    "audio_order_json",
  ];
}

function auditHeaders_() {
  return ["received_at", "event", "response_id", "details_json"];
}

function errorHeaders_() {
  return ["received_at", "message", "payload_excerpt"];
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}
