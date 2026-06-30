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
  dashboardMetricsSheetName: "dashboard_metrics",
  dashboardSheetName: "dashboard",
  codedOpenAnswersSheetName: "coded_open_answers",
  autoRebuildDashboardOnSubmit: false,
  markDashboardRebuildPendingOnSubmit: true,
  dashboardTriggerMinutes: 5,
  dashboardPendingProperty: "QUESTIONARIO_DASHBOARD_REBUILD_PENDING",
  dashboardPendingAtProperty: "QUESTIONARIO_DASHBOARD_REBUILD_PENDING_AT",
};

const DASHBOARD_OPEN_ANSWER_CATEGORIES = [
  "ruído de fundo",
  "eco",
  "voz abafada",
  "privacidade",
  "latência",
  "travamento",
  "dificuldade de configuração",
  "clareza da voz",
  "uso em chamadas",
  "outro",
];

const DASHBOARD_QUESTION_BLOCKS = [
  {
    id: "contexto",
    title: "Perfil/contexto do respondente e percepção de ruído",
    questions: [
      {
        id: "q_contextos_ruido",
        type: "checkbox",
        title: "Em quais situações o ruído mais prejudica sua comunicação por voz?",
        options: [
          "Reuniões online",
          "Chamadas de voz",
          "Aulas remotas",
          "Transporte público",
          "Ambientes industriais",
          "Jogos online",
          "Gravações de áudio",
          "Ambiente de trabalho",
        ],
      },
      {
        id: "q_tipos_ruido",
        type: "checkbox",
        title: "Quais tipos de ruído mais incomodam ou prejudicam a inteligibilidade da voz?",
        options: [
          "Ventilador ou ar-condicionado",
          "Trânsito",
          "Vozes ao fundo",
          "Teclado",
          "Televisão ou música",
          "Vento",
          "Motor",
          "Eco ou reverberação",
          "Ruído branco",
        ],
      },
      {
        id: "q_aplicacao_util",
        type: "radio",
        title: "Em qual aplicação a melhoria da voz seria mais útil para você?",
        options: [
          "Comunicação ao vivo, como chamadas e reuniões",
          "Gravação posterior, como vídeos, podcasts ou aulas",
          "Reconhecimento automático de fala ou legendas",
          "Monitoramento em ambiente profissional ou industrial",
        ],
      },
    ],
  },
  {
    id: "criterios",
    title: "Comparação perceptual dos métodos e critérios técnicos valorizados",
    questions: [
      {
        id: "q_caracteristicas_importantes",
        type: "checkbox",
        title: "Quais características você considera mais importantes em uma solução de redução de ruído de voz?",
        options: [
          "Baixa latência",
          "Voz natural",
          "Máxima remoção de ruído",
          "Funcionamento offline",
          "Baixo uso de CPU e memória",
          "Privacidade",
          "Compatibilidade com aplicativos Windows",
          "Facilidade de uso",
          "Estabilidade",
        ],
      },
      {
        id: "q_preferencia_metodo",
        type: "audio-choice",
        title: "Após ouvir exemplos comparáveis, qual método de redução de ruído você preferiria que fosse priorizado no protótipo?",
        options: [
          "rnnoise",
          "dfn3_default",
          "__unsure__",
        ],
      },
      {
        id: "q_troca_naturalidade_remocao",
        type: "scale",
        title: "Você aceitaria pequena perda de naturalidade da voz em troca de maior remoção de ruído?",
        min: 1,
        max: 5,
      },
      {
        id: "q_pior_erro",
        type: "radio",
        title: "O que seria pior em uma solução de redução de ruído?",
        options: [
          "Deixar a voz artificial ou metálica",
          "Cortar partes da fala",
          "Gerar atraso perceptível",
          "Funcionar bem só em alguns ambientes",
        ],
      },
    ],
  },
  {
    id: "acessibilidade",
    title: "Acessibilidade",
    questions: [
      {
        id: "q_barreiras_uso",
        type: "checkbox",
        title: "Quais fatores poderiam dificultar o uso de uma solução desse tipo por diferentes públicos?",
        options: [
          "Instalação de driver",
          "Necessidade de internet",
          "Configuração complicada",
          "Alto uso de CPU ou memória",
          "Interface complexa",
          "Falta de compatibilidade",
          "Falta de documentação",
          "Dificuldade para pessoas com deficiência auditiva, visual ou motora",
        ],
      },
      {
        id: "q_contextos_inclusao",
        type: "checkbox",
        title: "Em quais contextos uma ferramenta local de redução de ruído poderia ampliar o acesso à comunicação por voz?",
        options: [
          "Aulas remotas",
          "Reuniões de trabalho",
          "Atendimento ao público",
          "Ambientes compartilhados",
          "Pessoas com equipamentos simples",
          "Pessoas com conexão instável",
          "Produção de conteúdo educacional",
        ],
      },
    ],
  },
  {
    id: "sustentabilidade",
    title: "Sustentabilidade",
    questions: [
      {
        id: "q_offline_importante",
        type: "scale",
        title: "Você considera importante que a solução funcione sem internet?",
        min: 1,
        max: 5,
      },
      {
        id: "q_computadores_comuns",
        type: "scale",
        title: "Uma solução de redução de ruído deveria funcionar bem em computadores comuns ou mais antigos?",
        min: 1,
        max: 5,
      },
    ],
  },
  {
    id: "etica_privacidade",
    title: "Ética e privacidade",
    questions: [
      {
        id: "q_conforto_nuvem",
        type: "radio",
        title: "Você se sentiria confortável enviando sua voz para processamento em nuvem?",
        options: ["Sim", "Talvez, dependendo da aplicação", "Não"],
      },
      {
        id: "q_cuidado_etico",
        type: "checkbox",
        title: "Que cuidado ético você considera indispensável em uma solução que processa voz?",
        options: [
          "Não gravar nem armazenar a voz do usuário",
          "Explicar claramente quando o áudio está sendo processado",
          "Permitir desligar o processamento a qualquer momento",
          "Evitar envio automático de áudio a serviços externos",
          "Usar apenas dados públicos ou autorizados nos testes",
        ],
      },
    ],
  },
];

function setupQuestionarioReceiver() {
  const spreadsheet = getOrCreateSpreadsheet_();
  ensureSheets_(spreadsheet);
  Logger.log("Spreadsheet URL: " + spreadsheet.getUrl());
  Logger.log("Spreadsheet ID: " + spreadsheet.getId());
  return spreadsheet.getUrl();
}

function resetQuestionarioTestData() {
  const resetAt = new Date();
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const spreadsheet = getOrCreateSpreadsheet_();
    ensureSheets_(spreadsheet);

    const clearedSheets = [
      RECEIVER_CONFIG.rawSheetName,
      RECEIVER_CONFIG.wideSheetName,
      RECEIVER_CONFIG.dashboardMetricsSheetName,
      RECEIVER_CONFIG.codedOpenAnswersSheetName,
      RECEIVER_CONFIG.errorSheetName,
    ];
    clearedSheets.forEach(function(sheetName) {
      clearSheetDataRows_(spreadsheet, sheetName);
    });

    const dashboardResult = rebuildDashboardFromSpreadsheet_(spreadsheet, resetAt);
    appendAudit_(spreadsheet, "test_data_reset", "", {
      clearedSheets: clearedSheets,
      preservedSheets: [
        RECEIVER_CONFIG.schemaSheetName,
        RECEIVER_CONFIG.auditSheetName,
      ],
      totalResponses: dashboardResult.totalResponses,
      metricsRows: dashboardResult.metricsRows,
      updatedAt: dashboardResult.updatedAt,
    }, resetAt);

    Logger.log("Dados de teste limpos. Spreadsheet URL: " + spreadsheet.getUrl());
    return {
      ok: true,
      spreadsheetUrl: spreadsheet.getUrl(),
      clearedSheets: clearedSheets,
      preservedSheets: [
        RECEIVER_CONFIG.schemaSheetName,
        RECEIVER_CONFIG.auditSheetName,
      ],
      updatedAt: resetAt.toISOString(),
    };
  } finally {
    lock.releaseLock();
  }
}

function installQuestionarioDashboardTrigger() {
  removeQuestionarioDashboardTrigger();
  const trigger = ScriptApp.newTrigger("rebuildDashboardIfPending")
    .timeBased()
    .everyMinutes(RECEIVER_CONFIG.dashboardTriggerMinutes)
    .create();

  Logger.log("Trigger instalado para rebuildDashboardIfPending: " + trigger.getUniqueId());
  return {
    ok: true,
    handlerFunction: "rebuildDashboardIfPending",
    everyMinutes: RECEIVER_CONFIG.dashboardTriggerMinutes,
    triggerId: trigger.getUniqueId(),
  };
}

function removeQuestionarioDashboardTrigger() {
  const handlerName = "rebuildDashboardIfPending";
  const removed = [];
  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    if (trigger.getHandlerFunction && trigger.getHandlerFunction() === handlerName) {
      removed.push(trigger.getUniqueId());
      ScriptApp.deleteTrigger(trigger);
    }
  });

  if (removed.length) {
    Logger.log("Triggers removidos: " + removed.join(", "));
  }
  return {
    ok: true,
    removedTriggerIds: removed,
  };
}

function rebuildDashboardIfPending() {
  const properties = PropertiesService.getScriptProperties();
  if (properties.getProperty(RECEIVER_CONFIG.dashboardPendingProperty) !== "1") {
    return {
      ok: true,
      skipped: true,
      reason: "Sem rebuild pendente.",
    };
  }

  const updatedAt = new Date();
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    if (properties.getProperty(RECEIVER_CONFIG.dashboardPendingProperty) !== "1") {
      return {
        ok: true,
        skipped: true,
        reason: "Rebuild ja processado por outra execucao.",
      };
    }

    const spreadsheet = getOrCreateSpreadsheet_();
    ensureSheets_(spreadsheet);
    const pendingSince = properties.getProperty(RECEIVER_CONFIG.dashboardPendingAtProperty) || "";
    const result = rebuildDashboardFromSpreadsheet_(spreadsheet, updatedAt);
    properties.deleteProperty(RECEIVER_CONFIG.dashboardPendingProperty);
    properties.deleteProperty(RECEIVER_CONFIG.dashboardPendingAtProperty);
    appendAudit_(spreadsheet, "dashboard_trigger_rebuilt", "", {
      pendingSince: pendingSince,
      totalResponses: result.totalResponses,
      metricsRows: result.metricsRows,
      updatedAt: result.updatedAt,
    }, updatedAt);

    Logger.log("Dashboard reconstruido por trigger: " + JSON.stringify(result));
    return result;
  } finally {
    lock.releaseLock();
  }
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
      if (RECEIVER_CONFIG.autoRebuildDashboardOnSubmit) {
        const dashboardResult = rebuildDashboardFromSpreadsheet_(spreadsheet, receivedAt);
        appendAudit_(spreadsheet, "dashboard_auto_rebuilt", payload.responseId, {
          totalResponses: dashboardResult.totalResponses,
          metricsRows: dashboardResult.metricsRows,
          updatedAt: dashboardResult.updatedAt,
        }, receivedAt);
      } else if (RECEIVER_CONFIG.markDashboardRebuildPendingOnSubmit) {
        markDashboardRebuildPending_(payload.responseId, receivedAt);
        appendAudit_(spreadsheet, "dashboard_rebuild_pending", payload.responseId, {
          pendingAt: receivedAt.toISOString(),
          expectedTriggerMinutes: RECEIVER_CONFIG.dashboardTriggerMinutes,
        }, receivedAt);
      }
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
  ensureSheetWithHeaders_(spreadsheet, RECEIVER_CONFIG.dashboardMetricsSheetName, dashboardMetricHeaders_());
  ensureSheetWithHeaders_(spreadsheet, RECEIVER_CONFIG.codedOpenAnswersSheetName, codedOpenAnswersHeaders_());
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

function clearSheetDataRows_(spreadsheet, sheetName) {
  const sheet = spreadsheet.getSheetByName(sheetName);
  if (!sheet) {
    return;
  }

  const lastRow = sheet.getLastRow();
  const lastColumn = sheet.getLastColumn();
  if (lastRow > 1 && lastColumn > 0) {
    sheet.getRange(2, 1, lastRow - 1, lastColumn).clearContent();
  }
}

function markDashboardRebuildPending_(responseId, receivedAt) {
  const properties = PropertiesService.getScriptProperties();
  properties.setProperty(RECEIVER_CONFIG.dashboardPendingProperty, "1");
  properties.setProperty(
    RECEIVER_CONFIG.dashboardPendingAtProperty,
    JSON.stringify({
      responseId: responseId || "",
      receivedAt: receivedAt.toISOString(),
    }),
  );
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

function dashboardMetricHeaders_() {
  return [
    "updated_at",
    "block_id",
    "block_title",
    "question_id",
    "question_title",
    "question_type",
    "metric_type",
    "option_or_score",
    "n_valid",
    "count",
    "percent",
    "mean",
    "median",
    "rank",
    "questionnaire_id",
    "schema_version",
    "notes",
  ];
}

function codedOpenAnswersHeaders_() {
  return [
    "updated_at",
    "response_id",
    "questionnaire_id",
    "schema_version",
    "received_at",
    "question_id",
    "question_title",
    "answer_text",
    "manual_category",
    "manual_notes",
    "category_ruido_de_fundo",
    "category_eco",
    "category_voz_abafada",
    "category_privacidade",
    "category_latencia",
    "category_travamento",
    "category_dificuldade_de_configuracao",
    "category_clareza_da_voz",
    "category_uso_em_chamadas",
    "category_outro",
  ];
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}

/**
 * Reconstrói as abas de análise a partir de responses_raw.
 *
 * Esta função não altera responses_raw nem responses_wide. Ela pode ser
 * executada manualmente no Apps Script sempre que novas respostas forem
 * coletadas e for desejável atualizar o dashboard no Google Sheets.
 */
function rebuildDashboard() {
  const updatedAt = new Date();
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const spreadsheet = getOrCreateSpreadsheet_();
    const result = rebuildDashboardFromSpreadsheet_(spreadsheet, updatedAt);

    appendAudit_(spreadsheet, "dashboard_rebuilt", "", {
      totalResponses: result.totalResponses,
      metricsRows: result.metricsRows,
      updatedAt: result.updatedAt,
    }, updatedAt);

    return {
      ok: true,
      updatedAt: result.updatedAt,
      totalResponses: result.totalResponses,
      metricsRows: result.metricsRows,
      spreadsheetUrl: spreadsheet.getUrl(),
    };
  } finally {
    lock.releaseLock();
  }
}

function rebuildDashboardFromSpreadsheet_(spreadsheet, updatedAt) {
  ensureSheets_(spreadsheet);

  const records = readDashboardResponseRecords_(spreadsheet);
  const questionIndex = buildDashboardQuestionIndex_(records);
  const metricsRows = buildDashboardMetrics_(records, questionIndex, updatedAt);

  writeDashboardMetrics_(spreadsheet, metricsRows);
  writeCodedOpenAnswers_(spreadsheet, records, questionIndex, updatedAt);
  writeDashboardSheet_(spreadsheet, records, metricsRows, questionIndex, updatedAt);

  return {
    updatedAt: updatedAt.toISOString(),
    totalResponses: records.length,
    metricsRows: metricsRows.length,
  };
}

function readDashboardResponseRecords_(spreadsheet) {
  const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.rawSheetName);
  if (!sheet || sheet.getLastRow() < 2) {
    return [];
  }

  const values = sheet.getDataRange().getValues();
  const headers = values[0].map(String);
  const index = indexHeaders_(headers);
  const records = [];

  for (let rowIndex = 1; rowIndex < values.length; rowIndex += 1) {
    const row = values[rowIndex];
    const payload = parseJsonSafe_(cellValueByHeader_(row, index, "payload_json")) || {};
    const answers = payload.answers || parseJsonSafe_(cellValueByHeader_(row, index, "answers_json")) || {};
    const questionSnapshot = payload.questionSnapshot || parseJsonSafe_(cellValueByHeader_(row, index, "question_snapshot_json")) || [];
    const audioOrder = payload.audioOrder || parseJsonSafe_(cellValueByHeader_(row, index, "audio_order_json")) || [];
    const responseId = payload.responseId || cellValueByHeader_(row, index, "response_id") || "";

    records.push({
      rowNumber: rowIndex + 1,
      receivedAt: payload.receivedAt || cellValueByHeader_(row, index, "received_at") || "",
      responseId: responseId,
      questionnaireId: payload.questionnaireId || cellValueByHeader_(row, index, "questionnaire_id") || "",
      schemaVersion: payload.schemaVersion || cellValueByHeader_(row, index, "schema_version") || "",
      formDefinitionHash: payload.formDefinitionHash || cellValueByHeader_(row, index, "form_definition_hash") || "",
      audioManifestHash: payload.audioManifestHash || cellValueByHeader_(row, index, "audio_manifest_hash") || "",
      answers: answers,
      questionSnapshot: Array.isArray(questionSnapshot) ? questionSnapshot : [],
      audioOrder: Array.isArray(audioOrder) ? audioOrder : [],
      payload: payload,
    });
  }

  return records;
}

function buildDashboardQuestionIndex_(records) {
  const questions = {};
  const blocks = [];
  let order = 0;

  DASHBOARD_QUESTION_BLOCKS.forEach(function(block) {
    const blockCopy = {
      id: block.id,
      title: block.title,
      questionIds: [],
    };

    block.questions.forEach(function(question) {
      order += 1;
      const questionCopy = copyObject_(question);
      questionCopy.blockId = block.id;
      questionCopy.blockTitle = block.title;
      questionCopy.order = order;
      questions[question.id] = questionCopy;
      blockCopy.questionIds.push(question.id);
    });

    blocks.push(blockCopy);
  });

  const fallbackBlock = {
    id: "schema_antigo_ou_desconhecido",
    title: "Perguntas de schemas antigos ou não mapeadas",
    questionIds: [],
  };

  records.forEach(function(record) {
    (record.questionSnapshot || []).forEach(function(snapshotQuestion) {
      if (!snapshotQuestion || !snapshotQuestion.id) {
        return;
      }

      if (!questions[snapshotQuestion.id]) {
        order += 1;
        questions[snapshotQuestion.id] = {
          id: snapshotQuestion.id,
          type: snapshotQuestion.type || inferQuestionTypeFromAnswers_(records, snapshotQuestion.id) || "unknown",
          title: snapshotQuestion.title || snapshotQuestion.id,
          options: snapshotQuestion.options || null,
          blockId: fallbackBlock.id,
          blockTitle: fallbackBlock.title,
          order: order,
        };
        fallbackBlock.questionIds.push(snapshotQuestion.id);
      } else {
        if (!questions[snapshotQuestion.id].title && snapshotQuestion.title) {
          questions[snapshotQuestion.id].title = snapshotQuestion.title;
        }
        if (!questions[snapshotQuestion.id].type && snapshotQuestion.type) {
          questions[snapshotQuestion.id].type = snapshotQuestion.type;
        }
        if (!questions[snapshotQuestion.id].options && snapshotQuestion.options) {
          questions[snapshotQuestion.id].options = snapshotQuestion.options;
        }
      }
    });

    Object.keys(record.answers || {}).forEach(function(questionId) {
      if (questions[questionId]) {
        return;
      }
      const answer = record.answers[questionId] || {};
      order += 1;
      questions[questionId] = {
        id: questionId,
        type: answer.type || "unknown",
        title: answer.title || questionId,
        options: null,
        blockId: fallbackBlock.id,
        blockTitle: fallbackBlock.title,
        order: order,
      };
      fallbackBlock.questionIds.push(questionId);
    });
  });

  if (fallbackBlock.questionIds.length) {
    blocks.push(fallbackBlock);
  }

  return {
    blocks: blocks,
    questions: questions,
    audioLabels: buildAudioLabelMap_(records),
  };
}

function buildDashboardMetrics_(records, questionIndex, updatedAt) {
  const updatedIso = updatedAt.toISOString();
  const meta = buildDashboardMeta_(records);
  const rows = [];
  const orderedQuestions = Object.keys(questionIndex.questions)
    .map(function(questionId) {
      return questionIndex.questions[questionId];
    })
    .sort(function(a, b) {
      return (a.order || 0) - (b.order || 0);
    });

  orderedQuestions.forEach(function(question) {
    if (question.type === "checkbox" || question.type === "radio") {
      rows.push.apply(rows, buildFrequencyMetricRows_(records, question, questionIndex.audioLabels, updatedIso, meta, "frequency"));
      return;
    }

    if (question.type === "audio-choice") {
      rows.push.apply(rows, buildFrequencyMetricRows_(records, question, questionIndex.audioLabels, updatedIso, meta, "frequency"));
      rows.push.apply(rows, buildAudioPreferenceMetricRows_(records, question, questionIndex.audioLabels, updatedIso, meta));
      return;
    }

    if (question.type === "scale") {
      rows.push.apply(rows, buildScaleMetricRows_(records, question, updatedIso, meta));
      return;
    }

    if (question.type === "textarea") {
      rows.push(buildTextSummaryMetricRow_(records, question, updatedIso, meta));
    }
  });

  rows.push.apply(rows, buildAudioPreferenceRelationRows_(records, questionIndex, updatedIso, meta));
  return rows;
}

function buildFrequencyMetricRows_(records, question, audioLabels, updatedIso, meta, metricType) {
  const counts = {};
  let nValid = 0;

  records.forEach(function(record) {
    const values = answerValues_(record.answers[question.id], question.type);
    if (!values.length) {
      return;
    }
    nValid += 1;
    values.forEach(function(value) {
      const key = String(value);
      counts[key] = (counts[key] || 0) + 1;
    });
  });

  const options = optionValuesForQuestion_(question, counts);
  return options.map(function(option) {
    const optionKey = String(option);
    const count = counts[optionKey] || 0;
    return metricRow_(updatedIso, question, metricType, labelForOption_(question, optionKey, audioLabels), nValid, count, percent_(count, nValid), "", "", "", meta, "");
  });
}

function buildAudioPreferenceMetricRows_(records, question, audioLabels, updatedIso, meta) {
  const counts = {};
  let nValid = 0;

  records.forEach(function(record) {
    const values = answerValues_(record.answers[question.id], question.type);
    if (!values.length) {
      return;
    }
    const value = String(values[0]);
    nValid += 1;
    counts[value] = (counts[value] || 0) + 1;
  });

  const options = optionValuesForQuestion_(question, counts);
  const ranked = options.map(function(option) {
    const optionKey = String(option);
    return {
      option: optionKey,
      label: labelForOption_(question, optionKey, audioLabels),
      count: counts[optionKey] || 0,
    };
  }).sort(function(a, b) {
    if (b.count !== a.count) {
      return b.count - a.count;
    }
    return a.label.localeCompare(b.label);
  });

  return ranked.map(function(item, index) {
    return metricRow_(updatedIso, question, "audio_preference", item.label, nValid, item.count, percent_(item.count, nValid), "", "", index + 1, meta, "Preferência cega convertida para o rótulo técnico do método.");
  });
}

function buildScaleMetricRows_(records, question, updatedIso, meta) {
  const values = [];
  records.forEach(function(record) {
    const numeric = numericAnswer_(record.answers[question.id]);
    if (numeric !== null) {
      values.push(numeric);
    }
  });

  const nValid = values.length;
  const rows = [];
  const min = Number(question.min || Math.min.apply(null, values.concat([1])));
  const max = Number(question.max || Math.max.apply(null, values.concat([5])));
  const distribution = {};
  values.forEach(function(value) {
    const key = String(value);
    distribution[key] = (distribution[key] || 0) + 1;
  });

  rows.push(metricRow_(updatedIso, question, "scale_summary", "summary", nValid, "", "", mean_(values), median_(values), "", meta, "Resumo numérico da escala."));

  for (let score = min; score <= max; score += 1) {
    const key = String(score);
    const count = distribution[key] || 0;
    rows.push(metricRow_(updatedIso, question, "scale_distribution", key, nValid, count, percent_(count, nValid), "", "", "", meta, "Distribuição por nota."));
  }

  const categories = scaleCategoryCounts_(values, min, max);
  Object.keys(categories).forEach(function(category) {
    const count = categories[category];
    rows.push(metricRow_(updatedIso, question, "scale_category", category, nValid, count, percent_(count, nValid), "", "", "", meta, "Percentual por categoria agregada de escala."));
  });

  return rows;
}

function buildTextSummaryMetricRow_(records, question, updatedIso, meta) {
  let nValid = 0;
  records.forEach(function(record) {
    const text = textAnswer_(record.answers[question.id]);
    if (text) {
      nValid += 1;
    }
  });

  return metricRow_(updatedIso, question, "open_answer_summary", "respostas abertas preenchidas", nValid, nValid, percent_(nValid, records.length), "", "", "", meta, "As respostas abertas ficam em coded_open_answers para codificação manual.");
}

function buildAudioPreferenceRelationRows_(records, questionIndex, updatedIso, meta) {
  const preferenceQuestion = questionIndex.questions.q_preferencia_metodo;
  if (!preferenceQuestion) {
    return [];
  }

  const ratingQuestions = Object.keys(questionIndex.questions)
    .map(function(questionId) {
      return questionIndex.questions[questionId];
    })
    .filter(function(question) {
      return isSpecificAudioRatingQuestion_(question);
    });

  if (!ratingQuestions.length) {
    return [metricRow_(updatedIso, preferenceQuestion, "audio_preference_rating_note", "sem campos específicos", 0, "", "", "", "", "", meta, "Não foram encontrados campos específicos de qualidade, inteligibilidade ou naturalidade por áudio/método no schema atual.")];
  }

  const rows = [];
  ratingQuestions.forEach(function(ratingQuestion) {
    const grouped = {};
    records.forEach(function(record) {
      const preference = answerValues_(record.answers[preferenceQuestion.id], preferenceQuestion.type)[0];
      const rating = numericAnswer_(record.answers[ratingQuestion.id]);
      if (!preference || rating === null) {
        return;
      }
      const label = labelForOption_(preferenceQuestion, String(preference), questionIndex.audioLabels);
      if (!grouped[label]) {
        grouped[label] = [];
      }
      grouped[label].push(rating);
    });

    Object.keys(grouped).sort().forEach(function(label) {
      const values = grouped[label];
      rows.push(metricRow_(updatedIso, {
        id: preferenceQuestion.id + "__" + ratingQuestion.id,
        title: "Relação entre preferência de método e " + ratingQuestion.title,
        type: "scale",
        blockId: preferenceQuestion.blockId,
        blockTitle: preferenceQuestion.blockTitle,
      }, "audio_preference_rating", label, values.length, "", "", mean_(values), median_(values), "", meta, "Média da escala entre respondentes que preferiram este método."));
    });
  });

  return rows;
}

function writeDashboardMetrics_(spreadsheet, metricsRows) {
  const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.dashboardMetricsSheetName) || spreadsheet.insertSheet(RECEIVER_CONFIG.dashboardMetricsSheetName);
  writeSheetTable_(sheet, dashboardMetricHeaders_(), metricsRows);
}

function writeCodedOpenAnswers_(spreadsheet, records, questionIndex, updatedAt) {
  const sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.codedOpenAnswersSheetName) || spreadsheet.insertSheet(RECEIVER_CONFIG.codedOpenAnswersSheetName);
  const preserved = readExistingManualCoding_(sheet);
  const headers = codedOpenAnswersHeaders_();
  const rows = [];
  const updatedIso = updatedAt.toISOString();

  const openQuestions = Object.keys(questionIndex.questions)
    .map(function(questionId) {
      return questionIndex.questions[questionId];
    })
    .filter(function(question) {
      return question.type === "textarea";
    });

  records.forEach(function(record) {
    openQuestions.forEach(function(question) {
      const text = textAnswer_(record.answers[question.id]);
      if (!text) {
        return;
      }

      const key = manualCodingKey_(record.responseId, question.id);
      const manual = preserved[key] || {};
      rows.push(headers.map(function(header) {
        if (header === "updated_at") return updatedIso;
        if (header === "response_id") return record.responseId;
        if (header === "questionnaire_id") return record.questionnaireId;
        if (header === "schema_version") return record.schemaVersion;
        if (header === "received_at") return stringifyCell_(record.receivedAt);
        if (header === "question_id") return question.id;
        if (header === "question_title") return question.title;
        if (header === "answer_text") return text;
        if (manual[header] !== undefined) return manual[header];
        return "";
      }));
    });
  });

  writeSheetTable_(sheet, headers, rows);
  if (rows.length) {
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(DASHBOARD_OPEN_ANSWER_CATEGORIES, true)
      .setAllowInvalid(true)
      .build();
    sheet.getRange(2, 9, rows.length, 1).setDataValidation(rule);
  }
}

function writeDashboardSheet_(spreadsheet, records, metricsRows, questionIndex, updatedAt) {
  let sheet = spreadsheet.getSheetByName(RECEIVER_CONFIG.dashboardSheetName);
  if (!sheet) {
    sheet = spreadsheet.insertSheet(RECEIVER_CONFIG.dashboardSheetName);
  }

  sheet.clear();
  sheet.getCharts().forEach(function(chart) {
    sheet.removeChart(chart);
  });

  let row = 1;
  const meta = buildDashboardMeta_(records);
  const infoRows = [
    ["Dashboard do questionário extensionista PTC3527", ""],
    ["Atualizado em", updatedAt.toISOString()],
    ["questionnaireId", meta.questionnaireIds.join("; ") || "sem respostas"],
    ["schemaVersion", meta.schemaVersions.join("; ") || "sem respostas"],
    ["Total de respostas em responses_raw", records.length],
    ["Total de respostas válidas por métrica", "Consultar coluna n_valid em dashboard_metrics"],
    ["Observação de privacidade", "Os áudios dos usuários não são coletados, enviados ou armazenados pelo questionário."],
  ];
  writeRangeValues_(sheet, row, 1, infoRows);
  sheet.getRange(row, 1, 1, 2).setFontWeight("bold");
  row += infoRows.length + 2;

  row = writePreferenceSummarySection_(sheet, metricsRows, row);
  row += 1;

  questionIndex.blocks.forEach(function(block) {
    row = writeBlockDashboardSection_(sheet, metricsRows, questionIndex, block, row);
    row += 1;
  });

  if (sheet.getLastColumn() > 0) {
    sheet.autoResizeColumns(1, Math.min(sheet.getLastColumn(), 8));
  }
  sheet.setFrozenRows(1);
}

function writePreferenceSummarySection_(sheet, metricsRows, startRow) {
  const preferenceRows = metricsRows.filter(function(row) {
    return row[6] === "audio_preference";
  });

  sheet.getRange(startRow, 1).setValue("Resumo - preferência por método").setFontWeight("bold");
  let row = startRow + 1;

  const table = [["Método", "Votos", "Percentual", "Ranking"]];
  preferenceRows.forEach(function(metric) {
    table.push([metric[7], metric[9], metric[10], metric[13]]);
  });

  if (table.length === 1) {
    table.push(["Sem respostas válidas", 0, 0, ""]);
  }

  writeRangeValues_(sheet, row, 1, table);
  if (table.length > 1) {
    sheet.getRange(row + 1, 3, table.length - 1, 1).setNumberFormat("0.0\"%\"");
    addDashboardChart_(sheet, "bar", sheet.getRange(row, 1, table.length, 2), "Votos por método preferido", row, 6);
  }

  return row + table.length + 2;
}

function writeBlockDashboardSection_(sheet, metricsRows, questionIndex, block, startRow) {
  sheet.getRange(startRow, 1).setValue(block.title).setFontWeight("bold");
  let row = startRow + 1;

  block.questionIds.forEach(function(questionId) {
    const question = questionIndex.questions[questionId];
    if (!question) {
      return;
    }

    const questionRows = metricsRows.filter(function(metric) {
      return metric[3] === question.id;
    });

    if (!questionRows.length) {
      return;
    }

    sheet.getRange(row, 1).setValue(question.title).setFontWeight("bold");
    row += 1;

    if (question.type === "scale") {
      row = writeScaleQuestionDashboard_(sheet, question, questionRows, row);
      return;
    }

    if (question.type === "textarea") {
      const openSummary = questionRows.filter(function(metric) { return metric[6] === "open_answer_summary"; })[0];
      writeRangeValues_(sheet, row, 1, [["Respostas abertas preenchidas", openSummary ? openSummary[9] : 0, "Ver coded_open_answers para codificação manual"]]);
      row += 3;
      return;
    }

    const frequencyRows = questionRows.filter(function(metric) {
      return metric[6] === "frequency";
    });
    const table = [["Alternativa", "Contagem", "Percentual"]];
    frequencyRows.forEach(function(metric) {
      table.push([metric[7], metric[9], metric[10]]);
    });
    writeRangeValues_(sheet, row, 1, table);
    if (table.length > 1) {
      sheet.getRange(row + 1, 3, table.length - 1, 1).setNumberFormat("0.0\"%\"");
      addDashboardChart_(sheet, "bar", sheet.getRange(row, 1, table.length, 2), shortTitle_(question.title), row, 6);
    }
    row += table.length + 2;
  });

  return row;
}

function writeScaleQuestionDashboard_(sheet, question, questionRows, startRow) {
  let row = startRow;
  const summary = questionRows.filter(function(metric) { return metric[6] === "scale_summary"; })[0];
  const distribution = questionRows.filter(function(metric) { return metric[6] === "scale_distribution"; });
  const category = questionRows.filter(function(metric) { return metric[6] === "scale_category"; });
  const summaryTable = [["N", "Média", "Mediana"]];
  if (summary) {
    summaryTable.push([summary[8], summary[11], summary[12]]);
  } else {
    summaryTable.push([0, "", ""]);
  }
  writeRangeValues_(sheet, row, 1, summaryTable);
  row += summaryTable.length + 1;

  const distTable = [["Nota", "Contagem", "Percentual"]];
  distribution.forEach(function(metric) {
    distTable.push([metric[7], metric[9], metric[10]]);
  });
  writeRangeValues_(sheet, row, 1, distTable);
  if (distTable.length > 1) {
    sheet.getRange(row + 1, 3, distTable.length - 1, 1).setNumberFormat("0.0\"%\"");
    addDashboardChart_(sheet, "column", sheet.getRange(row, 1, distTable.length, 2), "Distribuição - " + shortTitle_(question.title), row, 6);
  }
  row += distTable.length + 1;

  const categoryTable = [["Categoria", "Contagem", "Percentual"]];
  category.forEach(function(metric) {
    categoryTable.push([metric[7], metric[9], metric[10]]);
  });
  writeRangeValues_(sheet, row, 1, categoryTable);
  if (categoryTable.length > 1) {
    sheet.getRange(row + 1, 3, categoryTable.length - 1, 1).setNumberFormat("0.0\"%\"");
  }
  return row + categoryTable.length + 2;
}

function writeSheetTable_(sheet, headers, rows) {
  sheet.clear();
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (rows.length) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
  sheet.setFrozenRows(1);
  if (sheet.getLastColumn() > 0) {
    sheet.autoResizeColumns(1, Math.min(sheet.getLastColumn(), 12));
  }
}

function writeRangeValues_(sheet, startRow, startColumn, values) {
  if (!values || !values.length) {
    return;
  }
  sheet.getRange(startRow, startColumn, values.length, values[0].length).setValues(values);
  sheet.getRange(startRow, startColumn, 1, values[0].length).setFontWeight("bold");
}

function addDashboardChart_(sheet, chartType, range, title, row, column) {
  let builder = sheet.newChart()
    .addRange(range)
    .setPosition(row, column, 0, 0)
    .setOption("title", title)
    .setOption("legend", { position: "none" });

  builder = chartType === "column" ? builder.asColumnChart() : builder.asBarChart();
  sheet.insertChart(builder.build());
}

function readExistingManualCoding_(sheet) {
  if (!sheet || sheet.getLastRow() < 2) {
    return {};
  }

  const values = sheet.getDataRange().getValues();
  const headers = values[0].map(String);
  const index = indexHeaders_(headers);
  const preserved = {};
  const manualHeaders = codedOpenAnswersHeaders_().filter(function(header) {
    return header === "manual_category" || header === "manual_notes" || header.indexOf("category_") === 0;
  });

  for (let rowIndex = 1; rowIndex < values.length; rowIndex += 1) {
    const row = values[rowIndex];
    const responseId = cellValueByHeader_(row, index, "response_id");
    const questionId = cellValueByHeader_(row, index, "question_id");
    if (!responseId || !questionId) {
      continue;
    }

    const entry = {};
    manualHeaders.forEach(function(header) {
      entry[header] = cellValueByHeader_(row, index, header);
    });
    preserved[manualCodingKey_(responseId, questionId)] = entry;
  }

  return preserved;
}

function metricRow_(updatedIso, question, metricType, optionOrScore, nValid, count, percent, mean, median, rank, meta, notes) {
  return [
    updatedIso,
    question.blockId || "",
    question.blockTitle || "",
    question.id || "",
    question.title || "",
    question.type || "",
    metricType || "",
    optionOrScore,
    nValid,
    count,
    percent,
    mean,
    median,
    rank,
    meta.questionnaireIds.join("; "),
    meta.schemaVersions.join("; "),
    notes || "",
  ];
}

function buildDashboardMeta_(records) {
  return {
    questionnaireIds: uniqueStrings_(records.map(function(record) { return record.questionnaireId; })),
    schemaVersions: uniqueStrings_(records.map(function(record) { return record.schemaVersion; })),
  };
}

function buildAudioLabelMap_(records) {
  const labels = {
    "__unsure__": "Não sei avaliar sem ouvir mais exemplos",
  };

  records.forEach(function(record) {
    (record.audioOrder || []).forEach(function(item) {
      if (!item || !item.audioId) {
        return;
      }
      labels[item.audioId] = item.methodLabel || item.choiceLabel || item.publicLabel || item.audioId;
    });
  });

  labels.rnnoise = labels.rnnoise || "RNNoise";
  labels.dfn3_default = labels.dfn3_default || "DeepFilterNet3 C API beta=1";
  return labels;
}

function optionValuesForQuestion_(question, counts) {
  const values = [];
  if (Array.isArray(question.options)) {
    question.options.forEach(function(option) {
      if (option !== null && option !== undefined && values.indexOf(String(option)) === -1) {
        values.push(String(option));
      }
    });
  }

  Object.keys(counts || {}).forEach(function(option) {
    if (values.indexOf(String(option)) === -1) {
      values.push(String(option));
    }
  });

  return values;
}

function labelForOption_(question, option, audioLabels) {
  if (question.type === "audio-choice") {
    return audioLabels[option] || option;
  }
  return option;
}

function answerValues_(answer, questionType) {
  if (!answer) {
    return [];
  }

  if (Array.isArray(answer.value)) {
    return answer.value.map(String).map(trimString_).filter(Boolean);
  }

  if (answer.value !== undefined && answer.value !== null && String(answer.value).trim() !== "") {
    return [String(answer.value).trim()];
  }

  if (answer.displayValue !== undefined && answer.displayValue !== null && String(answer.displayValue).trim() !== "") {
    const display = String(answer.displayValue).trim();
    if (questionType === "checkbox") {
      return display.split(";").map(trimString_).filter(Boolean);
    }
    return [display];
  }

  return [];
}

function numericAnswer_(answer) {
  const values = answerValues_(answer, "scale");
  if (!values.length) {
    return null;
  }
  const numeric = Number(values[0]);
  if (isNaN(numeric)) {
    return null;
  }
  return numeric;
}

function textAnswer_(answer) {
  const values = answerValues_(answer, "textarea");
  if (!values.length) {
    return "";
  }
  return String(values[0]).trim();
}

function inferQuestionTypeFromAnswers_(records, questionId) {
  for (let index = 0; index < records.length; index += 1) {
    const answer = records[index].answers && records[index].answers[questionId];
    if (answer && answer.type) {
      return answer.type;
    }
  }
  return "";
}

function isSpecificAudioRatingQuestion_(question) {
  const text = normalizeText_((question.id || "") + " " + (question.title || ""));
  if (text.indexOf("troca") !== -1 || text.indexOf("aceitaria") !== -1) {
    return false;
  }
  return question.type === "scale" && (
    text.indexOf("qualidade") !== -1 ||
    text.indexOf("inteligibilidade") !== -1 ||
    text.indexOf("naturalidade do audio") !== -1 ||
    text.indexOf("naturalidade da voz processada") !== -1
  );
}

function scaleCategoryCounts_(values, min, max) {
  const result = {
    "baixo": 0,
    "neutro": 0,
    "alto": 0,
  };

  values.forEach(function(value) {
    if (value <= min + 1) {
      result.baixo += 1;
    } else if (value >= max - 1) {
      result.alto += 1;
    } else {
      result.neutro += 1;
    }
  });

  return result;
}

function mean_(values) {
  if (!values.length) {
    return "";
  }
  const sum = values.reduce(function(accumulator, value) {
    return accumulator + value;
  }, 0);
  return sum / values.length;
}

function median_(values) {
  if (!values.length) {
    return "";
  }
  const sorted = values.slice().sort(function(a, b) {
    return a - b;
  });
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2) {
    return sorted[middle];
  }
  return (sorted[middle - 1] + sorted[middle]) / 2;
}

function percent_(count, denominator) {
  if (!denominator) {
    return 0;
  }
  return (Number(count) / Number(denominator)) * 100;
}

function uniqueStrings_(values) {
  const result = [];
  values.forEach(function(value) {
    const text = stringifyCell_(value).trim();
    if (text && result.indexOf(text) === -1) {
      result.push(text);
    }
  });
  return result;
}

function indexHeaders_(headers) {
  const index = {};
  headers.forEach(function(header, position) {
    index[String(header)] = position;
  });
  return index;
}

function cellValueByHeader_(row, index, header) {
  const position = index[header];
  if (position === undefined || position < 0 || position >= row.length) {
    return "";
  }
  return row[position];
}

function parseJsonSafe_(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  if (typeof value !== "string") {
    return value;
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    return null;
  }
}

function copyObject_(value) {
  return JSON.parse(JSON.stringify(value || {}));
}

function stringifyCell_(value) {
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function trimString_(value) {
  return String(value).trim();
}

function normalizeText_(value) {
  return String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function manualCodingKey_(responseId, questionId) {
  return String(responseId || "") + "::" + String(questionId || "");
}

function shortTitle_(title) {
  const text = String(title || "");
  return text.length > 70 ? text.substring(0, 67) + "..." : text;
}
