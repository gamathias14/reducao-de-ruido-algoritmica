(function () {
  "use strict";

  const config = window.QUESTIONARIO_CONFIG;
  const state = {
    startedAt: new Date(),
    audioOrder: [],
    questionNumber: 0,
    formDefinitionHash: "",
    audioManifestHash: "",
    localExperiment: {
      used: false,
      source: null,
      fileName: null,
      mimeType: null,
      sizeBytes: null,
      objectUrl: null,
      recordingSupported: false,
    },
    mediaRecorder: null,
    recordedChunks: [],
    currentStepIndex: 0,
    wizardSteps: [],
    totalQuestions: 0,
    wizardUnlocked: false,
  };

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    if (!config) {
      renderFatalError("Configuração do questionário não encontrada.");
      return;
    }

    state.audioOrder = buildAudioOrder();
    bindStaticText();
    renderBlocks();
    renderLocalExperiment();
    bindWizardNavigation();
    bindSubmit();

    state.formDefinitionHash = await sha256Json({
      questionnaireId: config.questionnaireId,
      schemaVersion: config.schemaVersion,
      blocks: config.blocks,
    });
    state.audioManifestHash = await sha256Json(config.audioComparison);
  }

  function bindStaticText() {
    setText("institution", config.institution);
    setText("page-title", config.title);
    setText("page-subtitle", config.subtitle);
    setText("project-title", config.projectTitle);
    setText("opening-text", config.privacy.openingText);
    setText("consent-label", config.privacy.consentLabel);
  }

  function renderBlocks() {
    const root = document.getElementById("form-root");
    root.innerHTML = "";
    state.questionNumber = 0;
    state.totalQuestions = config.blocks.reduce((total, block) => total + block.questions.length, 0);

    const shell = el("section", "wizard-shell");
    shell.setAttribute("aria-label", "Questionário por etapas");
    const viewport = el("div", "wizard-viewport");
    viewport.id = "wizard-viewport";

    config.blocks.forEach((block, blockIndex) => {
      block.questions.forEach((question) => {
        const step = el("section", "wizard-step");
        step.dataset.stepType = "question";
        step.dataset.questionId = question.id;
        step.dataset.blockId = block.id;
        step.dataset.blockIndex = String(blockIndex);
        step.hidden = true;

        state.questionNumber += 1;
        step.appendChild(renderStepContext(block, blockIndex, state.questionNumber));
        if (question.type === "audio-choice") {
          step.appendChild(renderAudioComparison());
        }
        step.appendChild(renderQuestion(question, state.questionNumber));
        viewport.appendChild(step);
      });
    });

    shell.appendChild(viewport);
    shell.appendChild(renderWizardNav());
    root.appendChild(shell);
  }

  function renderStepContext(block, blockIndex, questionNumber) {
    const context = el("div", "wizard-step-context");
    context.appendChild(el("span", "block-kicker", `Bloco ${blockIndex + 1} de ${config.blocks.length}`));
    context.appendChild(el("h2", "", block.title));
    if (block.description) {
      context.appendChild(el("p", "", block.description));
    }
    context.appendChild(el("span", "wizard-question-count", `Pergunta ${questionNumber} de ${state.totalQuestions}`));
    return context;
  }

  function renderWizardNav() {
    const nav = el("div", "wizard-nav");

    const prevButton = el("button", "wizard-button wizard-button--secondary", "← Anterior");
    prevButton.type = "button";
    prevButton.id = "wizard-prev";
    prevButton.setAttribute("aria-label", "Voltar para a pergunta anterior");

    const position = el("span", "wizard-position");
    position.id = "wizard-position";
    position.setAttribute("aria-live", "polite");

    const nextButton = el("button", "wizard-button wizard-button--primary", "Próxima →");
    nextButton.type = "button";
    nextButton.id = "wizard-next";
    nextButton.setAttribute("aria-label", "Avançar para a próxima pergunta");

    nav.append(prevButton, position, nextButton);
    return nav;
  }

  function renderQuestion(question, number) {
    const fieldset = el("fieldset", "question-card");
    fieldset.id = question.id;
    fieldset.dataset.questionId = question.id;
    fieldset.dataset.questionType = question.type;
    if (question.required) {
      fieldset.dataset.required = "true";
    }
    if (question.maxChoices) {
      fieldset.dataset.maxChoices = String(question.maxChoices);
    }
    if (question.maxLength) {
      fieldset.dataset.maxLength = String(question.maxLength);
    }

    const legend = el("legend", "", `P${number}. ${question.title}`);
    const body = el("div", "question-body");
    if (question.helpText) {
      body.appendChild(el("p", "help-text", question.helpText));
    }

    if (question.type === "checkbox") {
      body.appendChild(renderOptionList(question, "checkbox"));
    } else if (question.type === "radio") {
      body.appendChild(renderOptionList(question, "radio"));
    } else if (question.type === "audio-choice") {
      body.appendChild(renderAudioChoice(question));
    } else if (question.type === "scale") {
      body.appendChild(renderScale(question));
    } else if (question.type === "textarea") {
      body.appendChild(renderTextarea(question));
    } else {
      body.appendChild(el("p", "validation-summary", "Tipo de pergunta não suportado."));
    }

    fieldset.appendChild(legend);
    fieldset.appendChild(body);
    return fieldset;
  }

  function renderOptionList(question, inputType) {
    const wrapper = el("div", "option-grid");
    question.options.forEach((option, index) => {
      wrapper.appendChild(renderInputOption(question.id, inputType, option, `opt_${index}`));
    });

    if (question.other) {
      const other = el("label", "option-row other-row");
      const input = document.createElement("input");
      input.type = inputType;
      input.name = question.id;
      input.value = "__other__";
      input.dataset.otherToggle = question.id;

      const labelText = el("span", "other-label", "Outro:");
      const text = document.createElement("input");
      text.type = "text";
      text.className = "text-input";
      text.name = `${question.id}__other_text`;
      text.maxLength = 180;
      text.disabled = true;
      text.setAttribute("aria-label", `Outra resposta para ${question.title}`);

      const updateOtherState = () => {
        const shouldEnable = input.checked;
        text.disabled = !shouldEnable;
        other.classList.toggle("is-active", shouldEnable);
        if (!shouldEnable) {
          text.value = "";
        }
      };

      wrapper.addEventListener("change", () => {
        const wasDisabled = text.disabled;
        updateOtherState();
        if (input.checked && wasDisabled) {
          text.focus();
        }
      });

      other.appendChild(input);
      other.appendChild(labelText);
      other.appendChild(text);
      wrapper.appendChild(other);
      updateOtherState();
    }

    return wrapper;
  }

  function renderAudioChoice(question) {
    const wrapper = el("div", "option-grid");
    const choiceItems = state.audioOrder.filter((item) => item.choiceLabel && item.enabled);
    const options = choiceItems.length
      ? choiceItems.map((item) => ({
          id: item.id,
          value: item.id,
          label: config.audioComparison.blindLabels ? item.publicLabel : item.choiceLabel,
        }))
      : question.fallbackOptions.map((option, index) => ({
          id: `fallback_${index}`,
          value: option,
          label: option,
        }));

    options.forEach((option) => {
      wrapper.appendChild(renderInputOption(question.id, "radio", option.label, option.id, option.value));
    });
    wrapper.appendChild(
      renderInputOption(
        question.id,
        "radio",
        "Não sei avaliar sem ouvir mais exemplos",
        "nao_sei",
        "__unsure__",
      ),
    );

    return wrapper;
  }

  function renderInputOption(questionId, inputType, label, optionId, valueOverride) {
    const labelEl = el("label", "option-row");
    const input = document.createElement("input");
    input.type = inputType;
    input.name = questionId;
    input.value = valueOverride || label;
    input.id = `${questionId}_${safeId(optionId)}`;
    const span = el("span", "", label);
    labelEl.appendChild(input);
    labelEl.appendChild(span);
    return labelEl;
  }

  function renderScale(question) {
    const wrapper = el("div", "scale-row");
    wrapper.appendChild(el("span", "scale-label-left", question.leftLabel));

    const options = el("div", "scale-options");
    for (let value = question.min; value <= question.max; value += 1) {
      const label = el("label", "scale-option");
      const input = document.createElement("input");
      input.type = "radio";
      input.name = question.id;
      input.value = String(value);
      label.appendChild(input);
      label.appendChild(el("span", "", String(value)));
      options.appendChild(label);
    }
    wrapper.appendChild(options);
    wrapper.appendChild(el("span", "scale-label-right", question.rightLabel));
    return wrapper;
  }

  function renderTextarea(question) {
    const textarea = document.createElement("textarea");
    textarea.className = "textarea-input";
    textarea.name = question.id;
    textarea.maxLength = question.maxLength || 1200;
    textarea.rows = 5;
    return textarea;
  }

  function renderAudioComparison() {
    const panel = el("section", "audio-panel");
    panel.setAttribute("aria-labelledby", "audio-comparison-title");
    panel.appendChild(el("h3", "", config.audioComparison.title, { id: "audio-comparison-title" }));
    const body = el("div", "audio-body");
    body.appendChild(el("p", "help-text", config.audioComparison.description));

    const list = el("div", "audio-list");
    state.audioOrder.forEach((item) => {
      if (!item.enabled) {
        return;
      }
      const card = el("article", "audio-card");
      card.dataset.audioId = item.id;
      card.appendChild(el("h4", "", item.publicLabel));
      const noteText =
        config.audioComparison.blindLabels && item.choiceLabel
          ? "Exemplo processado para comparação."
          : item.note || "";
      card.appendChild(el("p", "audio-meta", noteText));
      if (item.src) {
        const audio = document.createElement("audio");
        audio.controls = true;
        audio.preload = "metadata";
        audio.src = item.src;
        audio.dataset.audioId = item.id;
        card.appendChild(audio);
      } else {
        card.appendChild(
          el(
            "p",
            "audio-placeholder",
            "Áudio ainda não configurado. Preencha o campo src no manifesto antes da coleta pública.",
          ),
        );
      }
      list.appendChild(card);
    });

    body.appendChild(list);
    panel.appendChild(body);
    return panel;
  }

  function renderLocalExperiment() {
    const section = document.getElementById("local-experiment");
    const localConfig = config.localExperiment;
    if (!localConfig || !localConfig.enabled) {
      return;
    }

    section.hidden = false;
    section.innerHTML = "";
    section.appendChild(el("h2", "", localConfig.title));
    section.appendChild(el("p", "", localConfig.description));

    const controls = el("div", "local-controls");

    const uploadControl = el("div", "local-control-card");
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "audio/*";
    fileInput.id = "local-audio-file";
    fileInput.className = "visually-hidden";
    fileInput.addEventListener("change", handleLocalFile);

    const fileLabel = el("label", "file-upload-button", "Carregar áudio");
    fileLabel.setAttribute("for", "local-audio-file");
    const fileName = el("span", "file-name", "Nenhum arquivo selecionado", { id: "local-audio-file-name" });
    uploadControl.appendChild(fileInput);
    uploadControl.appendChild(fileLabel);
    uploadControl.appendChild(fileName);
    controls.appendChild(uploadControl);

    const recordControl = el("div", "local-control-card local-control-card--action");
    const recordButton = el("button", "secondary-button", "Gravar no navegador");
    recordButton.type = "button";
    recordButton.id = "record-button";
    recordButton.addEventListener("click", toggleRecording);
    recordControl.appendChild(recordButton);
    controls.appendChild(recordControl);

    section.appendChild(controls);
    section.appendChild(el("p", "status-line", "", { id: "local-audio-status" }));

    const preview = document.createElement("audio");
    preview.id = "local-audio-preview";
    preview.controls = true;
    preview.hidden = true;
    section.appendChild(preview);

    const processorStatus = el(
      "p",
      "audio-placeholder",
      "Processadores locais ainda não carregados. Esta versão não envia nem processa o áudio próprio; ela apenas valida o fluxo seguro de gravação/carregamento local.",
    );
    section.appendChild(processorStatus);

    state.localExperiment.recordingSupported =
      Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
    if (!state.localExperiment.recordingSupported) {
      recordButton.disabled = true;
      setText("local-audio-status", "Gravação local não suportada neste navegador. Upload local ainda pode funcionar.");
    }
  }

  function handleLocalFile(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) {
      return;
    }
    setText("local-audio-file-name", file.name || "Áudio selecionado");
    registerLocalAudio(file, "upload");
  }

  async function toggleRecording() {
    const button = document.getElementById("record-button");
    if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
      state.mediaRecorder.stop();
      button.textContent = "Gravar no navegador";
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.recordedChunks = [];
      state.mediaRecorder = new MediaRecorder(stream);
      state.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          state.recordedChunks.push(event.data);
        }
      };
      state.mediaRecorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(state.recordedChunks, { type: state.mediaRecorder.mimeType || "audio/webm" });
        registerLocalAudio(blob, "recording", "gravacao-local.webm");
      };
      state.mediaRecorder.start();
      button.textContent = "Parar gravação";
      setText(
        "local-audio-status",
        `Gravando localmente. Limite recomendado: ${config.localExperiment.maxSeconds} segundos.`,
      );
      window.setTimeout(() => {
        if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
          state.mediaRecorder.stop();
          button.textContent = "Gravar no navegador";
        }
      }, config.localExperiment.maxSeconds * 1000);
    } catch (error) {
      setText("local-audio-status", "Não foi possível acessar o microfone neste navegador.");
    }
  }

  function registerLocalAudio(blobOrFile, source, fallbackName) {
    if (state.localExperiment.objectUrl) {
      URL.revokeObjectURL(state.localExperiment.objectUrl);
    }
    const objectUrl = URL.createObjectURL(blobOrFile);
    const preview = document.getElementById("local-audio-preview");
    preview.src = objectUrl;
    preview.hidden = false;

    state.localExperiment.used = true;
    state.localExperiment.source = source;
    state.localExperiment.fileName = blobOrFile.name || fallbackName || "audio-local";
    state.localExperiment.mimeType = blobOrFile.type || null;
    state.localExperiment.sizeBytes = blobOrFile.size || null;
    state.localExperiment.objectUrl = objectUrl;

    setText(
      "local-audio-status",
      "Áudio carregado apenas no navegador. Ele não será enviado na resposta do questionário.",
    );
  }

  function bindWizardNavigation() {
    const viewport = document.getElementById("wizard-viewport");
    const submitPanel = document.querySelector(".submit-panel");
    if (viewport && submitPanel && !submitPanel.closest(".wizard-step")) {
      const submitStep = el("section", "wizard-step wizard-step--submit");
      submitStep.dataset.stepType = "submit";
      submitStep.hidden = true;
      submitStep.appendChild(renderSubmitStepContext());
      submitStep.appendChild(submitPanel);
      viewport.appendChild(submitStep);
    }

    state.wizardSteps = Array.from(document.querySelectorAll(".wizard-step"));
    state.currentStepIndex = 0;

    const prevButton = document.getElementById("wizard-prev");
    const nextButton = document.getElementById("wizard-next");
    const form = document.getElementById("questionnaire-form");
    const consent = document.getElementById("consent");

    prevButton.addEventListener("click", () => {
      showWizardStep(state.currentStepIndex - 1, true);
    });

    nextButton.addEventListener("click", () => {
      if (!isCurrentStepReady()) {
        focusFirstInteractive_(state.wizardSteps[state.currentStepIndex]);
        return;
      }
      showWizardStep(state.currentStepIndex + 1, true);
    });

    form.addEventListener("change", updateWizardState);
    form.addEventListener("input", updateWizardState);
    consent.addEventListener("change", () => {
      if (consent.checked) {
        state.currentStepIndex = 0;
      }
      syncConsentGate(consent.checked, consent.checked);
    });

    syncConsentGate(consent.checked, false);
  }

  function renderSubmitStepContext() {
    const context = el("div", "wizard-step-context");
    context.appendChild(el("span", "block-kicker", "Revisão final"));
    context.appendChild(el("h2", "", "Envio das respostas"));
    context.appendChild(
      el("p", "", "Confira as respostas registradas no formulário antes de concluir a participação."),
    );
    return context;
  }

  function showWizardStep(nextIndex, shouldScroll) {
    if (!state.wizardSteps.length) {
      return;
    }

    const clampedIndex = Math.max(0, Math.min(nextIndex, state.wizardSteps.length - 1));
    state.currentStepIndex = clampedIndex;

    state.wizardSteps.forEach((step, index) => {
      const isCurrent = index === state.currentStepIndex;
      step.hidden = !isCurrent;
      step.setAttribute("aria-hidden", String(!isCurrent));
    });

    updateWizardState();

    if (shouldScroll) {
      document.querySelector(".wizard-shell").scrollIntoView({
        behavior: prefersReducedMotion_() ? "auto" : "smooth",
        block: "start",
      });
      window.setTimeout(
        () => focusFirstInteractive_(state.wizardSteps[state.currentStepIndex]),
        prefersReducedMotion_() ? 0 : 220,
      );
    }
  }

  function syncConsentGate(consentChecked, shouldScroll) {
    const shell = document.querySelector(".wizard-shell");
    if (!shell) {
      return;
    }

    state.wizardUnlocked = Boolean(consentChecked);
    shell.hidden = !state.wizardUnlocked;
    if (!state.wizardUnlocked) {
      return;
    }

    showWizardStep(state.currentStepIndex, shouldScroll);
  }

  function updateWizardState() {
    const prevButton = document.getElementById("wizard-prev");
    const nextButton = document.getElementById("wizard-next");
    const position = document.getElementById("wizard-position");
    const currentStep = state.wizardSteps[state.currentStepIndex];
    if (!prevButton || !nextButton || !position || !currentStep) {
      return;
    }

    const isSubmitStep = currentStep.dataset.stepType === "submit";
    const ready = isCurrentStepReady();
    const lastQuestionIndex = state.wizardSteps.findIndex((step) => step.dataset.stepType === "submit") - 1;

    prevButton.disabled = state.currentStepIndex === 0;
    nextButton.hidden = isSubmitStep;
    nextButton.disabled = !ready || isSubmitStep;
    nextButton.classList.toggle("is-ready", ready && !isSubmitStep);
    nextButton.textContent = state.currentStepIndex === lastQuestionIndex ? "Revisar envio →" : "Próxima →";

    if (isSubmitStep) {
      position.textContent = "Revisão final";
    } else {
      position.textContent = `Pergunta ${state.currentStepIndex + 1} de ${state.totalQuestions}`;
    }
  }

  function isCurrentStepReady() {
    const currentStep = state.wizardSteps[state.currentStepIndex];
    if (!currentStep || currentStep.dataset.stepType === "submit") {
      return true;
    }

    const question = findQuestionById(currentStep.dataset.questionId);
    if (!question) {
      return true;
    }

    const answer = readQuestionAnswer(question);
    return isQuestionAnswerReady(question, answer);
  }

  function findQuestionById(questionId) {
    for (const block of config.blocks) {
      const found = block.questions.find((question) => question.id === questionId);
      if (found) {
        return found;
      }
    }
    return null;
  }

  function isQuestionAnswerReady(question, answer) {
    if (!question.required) {
      return true;
    }
    if (!answer || isEmptyAnswer(answer)) {
      return false;
    }
    if (question.type === "checkbox" && question.maxChoices && answer.value.length > question.maxChoices) {
      return false;
    }
    if (question.type === "textarea" && question.maxLength && answer.value.length > question.maxLength) {
      return false;
    }
    return true;
  }

  function focusFirstInteractive_(target) {
    const focusable = target.matches("input, textarea, button, audio")
      ? target
      : target.querySelector("input:not(:disabled), textarea:not(:disabled), button:not(:disabled), audio");
    if (focusable && typeof focusable.focus === "function") {
      focusable.focus({ preventScroll: true });
    }
  }

  function prefersReducedMotion_() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function bindSubmit() {
    const form = document.getElementById("questionnaire-form");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearSubmissionStatus();
      const submitButton = form.querySelector(".primary-button");

      const validation = validateForm();
      if (!validation.ok) {
        showValidationErrors(validation.errors);
        return;
      }

      const payload = buildPayload();
      if (!config.submission.enabled || !config.submission.endpoint) {
        showSubmissionStatus(
          "Pré-visualização validada. O envio real ainda não está habilitado.",
          "success",
        );
        console.info("Payload de pré-visualização do questionário:", payload);
        return;
      }

      try {
        submitButton.disabled = true;
        submitButton.dataset.originalLabel = submitButton.textContent;
        submitButton.textContent = "Enviando...";
        showSubmissionStatus("Enviando respostas...", "pending");
        await fetch(config.submission.endpoint, {
          method: "POST",
          mode: "no-cors",
          headers: {
            "Content-Type": "text/plain;charset=utf-8",
          },
          body: JSON.stringify(payload),
        });
        showSubmissionStatus("Respostas recebidas. Obrigado pela contribuição.", "success");
        submitButton.textContent = "Enviado";
      } catch (error) {
        submitButton.disabled = false;
        submitButton.textContent = submitButton.dataset.originalLabel || "Enviar respostas";
        showSubmissionStatus("Não foi possível enviar agora. Tente novamente em instantes.", "error");
      }
    });
  }

  function validateForm() {
    const errors = [];
    const consent = document.getElementById("consent");
    const honeypot = document.getElementById("website");

    if (!consent.checked) {
      errors.push({ message: "Confirme o consentimento antes de enviar.", targetId: "consent" });
    }
    if (honeypot.value.trim()) {
      errors.push({ message: "Falha de validação do formulário.", targetId: "website" });
    }

    allQuestions().forEach((question) => {
      const fieldset = document.querySelector(`[data-question-id="${question.id}"]`);
      if (!fieldset) {
        return;
      }
      const value = readQuestionAnswer(question);
      if (question.required && isEmptyAnswer(value)) {
        errors.push({ message: `Responda: ${question.title}`, targetId: question.id });
      }
      if (question.type === "checkbox" && question.maxChoices && Array.isArray(value.value)) {
        if (value.value.length > question.maxChoices) {
          errors.push({
            message: `Escolha no máximo ${question.maxChoices} opções em: ${question.title}`,
            targetId: question.id,
          });
        }
      }
      if (question.type === "textarea" && question.maxLength && value.value.length > question.maxLength) {
        errors.push({
          message: `A resposta aberta ultrapassa ${question.maxLength} caracteres.`,
          targetId: question.id,
        });
      }
    });

    return { ok: errors.length === 0, errors };
  }

  function readQuestionAnswer(question) {
    if (question.type === "checkbox") {
      const checked = Array.from(document.querySelectorAll(`input[name="${question.id}"]:checked`));
      const values = checked
        .map((input) => {
          if (input.value === "__other__") {
            const other = document.querySelector(`input[name="${question.id}__other_text"]`);
            return other && other.value.trim() ? `Outro: ${other.value.trim()}` : "";
          }
          return input.value;
        })
        .filter(Boolean);
      return { type: question.type, title: question.title, value: values, displayValue: values.join("; ") };
    }

    if (question.type === "radio" || question.type === "audio-choice" || question.type === "scale") {
      const selected = document.querySelector(`input[name="${question.id}"]:checked`);
      let value = selected ? selected.value : "";
      let displayValue = value;

      if (value === "__other__") {
        const other = document.querySelector(`input[name="${question.id}__other_text"]`);
        value = other && other.value.trim() ? `Outro: ${other.value.trim()}` : "";
        displayValue = value;
      } else if (question.type === "audio-choice") {
        displayValue = audioDisplayValue(value);
      }

      return { type: question.type, title: question.title, value, displayValue };
    }

    if (question.type === "textarea") {
      const textarea = document.querySelector(`textarea[name="${question.id}"]`);
      const value = textarea ? textarea.value.trim() : "";
      return { type: question.type, title: question.title, value, displayValue: value };
    }

    return { type: question.type, title: question.title, value: "", displayValue: "" };
  }

  function buildPayload() {
    const submittedAt = new Date();
    const answers = {};
    allQuestions().forEach((question) => {
      answers[question.id] = readQuestionAnswer(question);
    });

    return {
      responseId: cryptoRandomId(),
      questionnaireId: config.questionnaireId,
      schemaVersion: config.schemaVersion,
      submittedAt: submittedAt.toISOString(),
      startedAt: state.startedAt.toISOString(),
      elapsedMs: submittedAt.getTime() - state.startedAt.getTime(),
      formDefinitionHash: state.formDefinitionHash,
      audioManifestHash: state.audioManifestHash,
      page: {
        href: window.location.href,
        userAgent: navigator.userAgent,
        language: navigator.language,
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      },
      audioOrder: state.audioOrder.map((item, index) => ({
        position: index + 1,
        publicLabel: item.publicLabel,
        audioId: item.id,
        methodLabel: item.methodLabel,
        choiceLabel: item.choiceLabel,
        src: item.src || "",
        sha256: item.sha256 || "",
        enabled: item.enabled,
        hasSource: Boolean(item.src),
      })),
      localExperiment: {
        used: state.localExperiment.used,
        source: state.localExperiment.source,
        fileName: state.localExperiment.fileName,
        mimeType: state.localExperiment.mimeType,
        sizeBytes: state.localExperiment.sizeBytes,
        audioSent: false,
      },
      answers,
      questionSnapshot: allQuestions().map((question) => ({
        id: question.id,
        type: question.type,
        title: question.title,
        required: Boolean(question.required),
        options: question.options || question.fallbackOptions || null,
      })),
    };
  }

  function showValidationErrors(errors) {
    const summary = document.getElementById("validation-summary");
    summary.hidden = false;
    summary.innerHTML = "";
    summary.appendChild(el("strong", "", "Revise os pontos abaixo:"));
    const list = document.createElement("ul");
    errors.forEach((error) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = error.targetId === "consent" ? "#consent" : `#${error.targetId}`;
      link.textContent = error.message;
      link.addEventListener("click", (event) => {
        event.preventDefault();
        focusTarget(error.targetId);
      });
      item.appendChild(link);
      list.appendChild(item);
    });
    summary.appendChild(list);
    summary.focus();
  }

  function focusTarget(targetId) {
    const direct = document.getElementById(targetId);
    const fieldset = document.querySelector(`[data-question-id="${targetId}"]`);
    const target = direct || fieldset;
    if (target) {
      const step = target.closest(".wizard-step");
      if (step) {
        const stepIndex = state.wizardSteps.indexOf(step);
        if (stepIndex >= 0) {
          showWizardStep(stepIndex, false);
        }
      }
      target.scrollIntoView({ block: "center", behavior: prefersReducedMotion_() ? "auto" : "smooth" });
      const focusable = target.matches("input, textarea, button")
        ? target
        : target.querySelector("input, textarea, button");
      if (focusable) {
        focusable.focus();
      }
    }
  }

  function clearSubmissionStatus() {
    const summary = document.getElementById("validation-summary");
    summary.hidden = true;
    summary.innerHTML = "";
    showSubmissionStatus("", "");
  }

  function showSubmissionStatus(message, kind) {
    const status = document.getElementById("submission-status");
    status.textContent = message;
    status.className = `submission-status ${kind || ""}`.trim();
  }

  function buildAudioOrder() {
    const items = (config.audioComparison.items || []).map((item) => ({ ...item }));
    const enabledReferenceItems = items.filter((item) => item.enabled && !item.choiceLabel);
    const enabledChoiceItems = items.filter((item) => item.enabled && item.choiceLabel);
    const disabledItems = items.filter((item) => !item.enabled);
    const orderedChoices = config.audioComparison.randomize ? shuffle(enabledChoiceItems) : enabledChoiceItems;

    enabledReferenceItems.forEach((item) => {
      item.publicLabel = config.audioComparison.blindLabels ? "Referência ruidosa" : item.methodLabel;
    });
    orderedChoices.forEach((item, index) => {
      item.publicLabel = config.audioComparison.blindLabels
        ? `Áudio ${String.fromCharCode(65 + index)}`
        : item.methodLabel;
    });
    disabledItems.forEach((item) => {
      item.publicLabel = item.methodLabel;
    });
    return enabledReferenceItems.concat(orderedChoices, disabledItems);
  }

  function audioDisplayValue(value) {
    if (value === "__unsure__") {
      return "Não sei avaliar sem ouvir mais exemplos";
    }
    const item = state.audioOrder.find((audio) => audio.id === value);
    if (!item) {
      return value;
    }
    return `${item.publicLabel} (${item.methodLabel})`;
  }

  function allQuestions() {
    return config.blocks.flatMap((block) => block.questions);
  }

  function isEmptyAnswer(answer) {
    if (Array.isArray(answer.value)) {
      return answer.value.length === 0;
    }
    return !String(answer.value || "").trim();
  }

  async function sha256Json(value) {
    if (!window.crypto || !window.crypto.subtle) {
      return "sha256-unavailable";
    }
    const data = new TextEncoder().encode(JSON.stringify(value));
    const hashBuffer = await window.crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(hashBuffer))
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  function cryptoRandomId() {
    if (window.crypto && window.crypto.randomUUID) {
      return window.crypto.randomUUID();
    }
    if (!window.crypto || !window.crypto.getRandomValues) {
      return `response-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    return Array.from(bytes)
      .map((byte) => byte.toString(16).padStart(2, "0"))
      .join("");
  }

  function shuffle(items) {
    const copy = items.slice();
    for (let index = copy.length - 1; index > 0; index -= 1) {
      const randomIndex = Math.floor(Math.random() * (index + 1));
      [copy[index], copy[randomIndex]] = [copy[randomIndex], copy[index]];
    }
    return copy;
  }

  function safeId(value) {
    return String(value).replace(/[^a-zA-Z0-9_-]+/g, "_");
  }

  function setText(id, text) {
    const node = document.getElementById(id);
    if (node) {
      node.textContent = text || "";
    }
  }

  function el(tag, className, text, attrs) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined && text !== null) {
      node.textContent = text;
    }
    if (attrs) {
      Object.keys(attrs).forEach((key) => node.setAttribute(key, attrs[key]));
    }
    return node;
  }

  function renderFatalError(message) {
    document.body.innerHTML = "";
    const main = el("main", "page-shell");
    main.appendChild(el("div", "validation-summary", message));
    document.body.appendChild(main);
  }
})();
