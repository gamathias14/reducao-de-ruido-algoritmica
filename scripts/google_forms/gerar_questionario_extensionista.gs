/**
 * Gera o Google Forms do questionario extensionista do PTC3527.
 *
 * Como usar:
 * 1. Abra https://script.google.com/ e crie um novo projeto.
 * 2. Cole este arquivo em Code.gs.
 * 3. Preencha AUDIO_COMPARISON_URLS com links do Mote, Drive ou YouTube.
 * 4. Execute criarQuestionarioExtensionista().
 * 5. Autorize o script e copie as URLs exibidas em "Executions" ou "Logs".
 *
 * Observacao importante:
 * Google Forms nao possui item nativo de audio no FormApp. Para audio, use links
 * do Mote ou do Google Drive no texto da secao. Links do Mote podem tocar dentro
 * do formulario para respondentes com a extensao Mote instalada; sem a extensao,
 * o respondente ve o link e ouve no site do Mote. Para player nativo do Forms,
 * converta cada audio em video simples e use URLs do YouTube, que o Forms aceita
 * como VideoItem.
 */

const FORM_CONFIG = {
  title: 'Questionario extensionista - reducao de ruido local para voz humana',
  collectEmail: false,
  allowResponseEdits: false,
  limitOneResponsePerUser: false,
  destinationSpreadsheetName: 'Respostas - questionario extensionista PTC3527',
  description: [
    'Este questionario integra a atividade extensionista da disciplina PTC3527 - Anteprojeto de Formatura em Telecomunicacoes, da Escola Politecnica da USP.',
    'O projeto investiga reducao de ruido local para voz humana no Windows, combinando avaliacao de algoritmos, processamento causal e integracao com um microfone virtual.',
    'A participacao e voluntaria. Nao e necessario informar nome, documento, endereco ou enviar gravacoes de voz.',
    'As respostas serao analisadas de forma agregada e usadas para orientar requisitos tecnicos do projeto.'
  ].join('\n\n')
};

const AUDIO_COMPARISON_URLS = [
  {
    label: 'Referencia ruidosa',
    methodChoice: null,
    url: '',
    note: 'Preencher com link do Mote, Drive ou YouTube.'
  },
  {
    label: 'RNNoise',
    methodChoice: 'RNNoise, candidato principal selecionado no benchmark',
    url: '',
    note: 'Candidato principal.'
  },
  {
    label: 'OM-LSA/IMCRA',
    methodChoice: 'OM-LSA/IMCRA, reserva com maior preservacao perceptual',
    url: '',
    note: 'Reserva final.'
  },
  {
    label: 'STFT causal adaptativa',
    methodChoice: 'STFT causal adaptativa, baseline operacional de referencia',
    url: '',
    note: 'Baseline operacional.'
  },
  {
    label: 'WebRTC APM NS',
    methodChoice: 'WebRTC APM NS',
    url: '',
    note: 'Opcional: preencher se quiser expor alternativa nao selecionada.'
  },
  {
    label: 'DeepFilterNet3',
    methodChoice: 'DeepFilterNet3',
    url: '',
    note: 'Opcional: preencher se quiser expor alternativa nao selecionada.'
  },
  {
    label: 'Wavelet/WPT causal',
    methodChoice: 'Wavelet/WPT causal',
    url: '',
    note: 'Opcional: preencher se quiser expor alternativa nao selecionada.'
  }
];

const FORM_BLOCKS = [
  {
    title: 'Bloco 1 - Contexto de uso e relevancia do problema',
    questions: [
      {
        type: 'checkbox',
        title: 'Em quais situacoes o ruido mais prejudica sua comunicacao por voz?',
        helpText: 'Multipla selecao.',
        required: true,
        options: [
          'Reunioes online',
          'Chamadas de voz',
          'Aulas remotas',
          'Transporte publico',
          'Ambientes industriais',
          'Jogos online',
          'Gravacoes de audio',
          'Ambiente de trabalho'
        ],
        other: true,
        projectUse: 'definir cenarios prioritarios de teste e exemplos de aplicacao a serem discutidos no relatorio.'
      },
      {
        type: 'checkbox',
        title: 'Quais tipos de ruido mais incomodam ou prejudicam a inteligibilidade da voz?',
        helpText: 'Multipla selecao.',
        required: true,
        options: [
          'Ventilador ou ar-condicionado',
          'Transito',
          'Vozes ao fundo',
          'Teclado',
          'Televisao ou musica',
          'Vento',
          'Motor',
          'Eco ou reverberacao',
          'Ruido branco'
        ],
        other: true,
        projectUse: 'priorizar ruidos em bases publicas, misturas sinteticas e graficos comparativos.'
      },
      {
        type: 'multipleChoice',
        title: 'Em qual aplicacao a melhoria da voz seria mais util para voce?',
        helpText: 'Escolha unica.',
        required: true,
        options: [
          'Comunicacao ao vivo, como chamadas e reunioes',
          'Gravacao posterior, como videos, podcasts ou aulas',
          'Reconhecimento automatico de fala ou legendas',
          'Monitoramento em ambiente profissional ou industrial'
        ],
        other: true,
        projectUse: 'ajustar a enfase entre latencia, qualidade final e inteligibilidade para sistemas automaticos.'
      }
    ]
  },
  {
    title: 'Bloco 2 - Criterios tecnicos e requisitos do sistema',
    questions: [
      {
        type: 'checkbox',
        title: 'Quais caracteristicas voce considera mais importantes em uma solucao de reducao de ruido de voz?',
        helpText: 'Escolha ate tres opcoes.',
        required: true,
        maxChoices: 3,
        options: [
          'Baixa latencia',
          'Voz natural',
          'Maxima remocao de ruido',
          'Funcionamento offline',
          'Baixo uso de CPU e memoria',
          'Privacidade',
          'Compatibilidade com aplicativos Windows',
          'Facilidade de uso',
          'Estabilidade'
        ],
        projectUse: 'definir pesos qualitativos para comparar qualidade, custo computacional, privacidade, estabilidade e integracao com aplicativos Windows.'
      },
      {
        type: 'audioComparison',
        title: 'Exemplos comparaveis de audio',
        helpText: 'Antes de responder a proxima pergunta, ouca os exemplos disponiveis. Use fones de ouvido, se possivel, e mantenha volume semelhante entre os exemplos.'
      },
      {
        type: 'multipleChoice',
        title: 'Apos ouvir exemplos comparaveis, qual metodo de reducao de ruido voce preferiria que fosse priorizado no prototipo?',
        helpText: 'Escolha unica.',
        required: true,
        optionsFromAudio: true,
        fallbackOptions: [
          'RNNoise, candidato principal selecionado no benchmark',
          'OM-LSA/IMCRA, reserva com maior preservacao perceptual',
          'STFT causal adaptativa, baseline operacional de referencia',
          'WebRTC APM NS',
          'DeepFilterNet3',
          'Wavelet/WPT causal',
          'Nao sei avaliar sem ouvir mais exemplos'
        ],
        projectUse: 'validar com o publico a escolha perceptual entre RNNoise, reservas e alternativas que nao avancaram na selecao tecnica.'
      },
      {
        enabled: false,
        type: 'multipleChoice',
        title: 'Qual atraso maximo voce considera aceitavel em uma comunicacao por voz ao vivo?',
        helpText: 'Pergunta mantida desativada por risco de resposta obvia ou pouco operacional.',
        options: [
          'Imperceptivel',
          'Ate 50 ms',
          'Ate 100 ms',
          'Mais de 100 ms',
          'Nao sei avaliar'
        ],
        projectUse: 'orientar tamanho de janelas, buffers, salto da STFT, tamanho de blocos e meta de atraso para comunicacao ao vivo.'
      },
      {
        type: 'scale',
        title: 'Voce aceitaria pequena perda de naturalidade da voz em troca de maior remocao de ruido?',
        helpText: 'Escala de 1 a 5.',
        required: true,
        leftLabel: 'Nao aceitaria',
        rightLabel: 'Aceitaria totalmente',
        projectUse: 'calibrar agressividade de subtracao espectral, ganho espectral e limiares Wavelet.'
      },
      {
        type: 'multipleChoice',
        title: 'O que seria pior em uma solucao de reducao de ruido?',
        helpText: 'Escolha unica.',
        required: true,
        options: [
          // 'Deixar ruido demais',
          'Deixar a voz artificial ou metalica',
          'Cortar partes da fala',
          'Gerar atraso perceptivel',
          'Funcionar bem so em alguns ambientes'
        ],
        projectUse: 'identificar qual tipo de erro deve receber maior atencao na analise qualitativa e nos ajustes de parametros.'
      }
    ]
  },
  {
    title: 'Bloco 3 - Acessibilidade e inclusao',
    questions: [
      {
        type: 'checkbox',
        title: 'Quais fatores poderiam dificultar o uso de uma solucao desse tipo por diferentes publicos?',
        helpText: 'Multipla selecao.',
        required: true,
        options: [
          'Instalacao de driver',
          'Necessidade de internet',
          'Configuracao complicada',
          'Alto uso de CPU ou memoria',
          'Interface complexa',
          'Falta de compatibilidade',
          'Falta de documentacao',
          'Dificuldade para pessoas com deficiencia auditiva, visual ou motora'
        ],
        other: true,
        projectUse: 'informar requisitos de instalacao, compatibilidade, simplicidade operacional e acessibilidade no Windows.'
      },
      {
        type: 'checkbox',
        title: 'Em quais contextos uma ferramenta local de reducao de ruido poderia ampliar o acesso a comunicacao por voz?',
        helpText: 'Multipla selecao.',
        required: true,
        options: [
          'Aulas remotas',
          'Reunioes de trabalho',
          'Atendimento ao publico',
          'Ambientes compartilhados',
          'Pessoas com equipamentos simples',
          'Pessoas com conexao instavel',
          'Producao de conteudo educacional'
        ],
        other: true,
        projectUse: 'relacionar o prototipo a cenarios de inclusao, acesso e comunicacao em condicoes tecnicas limitadas.'
      }
    ]
  },
  {
    title: 'Bloco 4 - Sustentabilidade',
    questions: [
      {
        type: 'scale',
        title: 'Voce considera importante que a solucao funcione sem internet?',
        helpText: 'Escala de 1 a 5.',
        required: true,
        leftLabel: 'Pouco importante',
        rightLabel: 'Muito importante',
        projectUse: 'justificar processamento local, reduzir dependencia de infraestrutura externa e avaliar a relevancia de evitar nuvem.'
      },
      {
        type: 'scale',
        title: 'Uma solucao de reducao de ruido deveria funcionar bem em computadores comuns ou mais antigos?',
        helpText: 'Escala de 1 a 5.',
        required: true,
        leftLabel: 'Pouco importante',
        rightLabel: 'Muito importante',
        projectUse: 'orientar limites de CPU, memoria e energia para evitar uma solucao restrita a maquinas de alto desempenho.'
      },
      {
        enabled: false,
        type: 'scale',
        title: 'O uso de CPU e memoria deveria influenciar a escolha do metodo de reducao de ruido?',
        helpText: 'Pergunta mantida desativada por risco de resposta obvia ou pouco operacional.',
        leftLabel: 'Pouco importante',
        rightLabel: 'Muito importante',
        projectUse: 'relacionar qualidade de audio com custo computacional, estabilidade e execucao continua no Windows.'
      }
    ]
  },
  {
    title: 'Bloco 5 - Etica e privacidade',
    questions: [
      {
        type: 'multipleChoice',
        title: 'Voce se sentiria confortavel enviando sua voz para processamento em nuvem?',
        helpText: 'Escolha unica.',
        required: true,
        options: [
          'Sim',
          'Talvez, dependendo da aplicacao',
          'Nao'
        ],
        projectUse: 'orientar a discussao sobre privacidade, processamento local e ausencia de coleta de voz no projeto.'
      },
      {
        type: 'checkbox',
        title: 'Que cuidado etico voce considera indispensavel em uma solucao que processa voz?',
        helpText: 'Escolha ate duas opcoes.',
        required: true,
        maxChoices: 2,
        options: [
          'Nao gravar nem armazenar a voz do usuario',
          'Explicar claramente quando o audio esta sendo processado',
          'Permitir desligar o processamento a qualquer momento',
          'Evitar envio automatico de audio a servicos externos',
          'Usar apenas dados publicos ou autorizados nos testes'
        ],
        other: true,
        projectUse: 'definir salvaguardas de consentimento, transparencia, processamento local e uso responsavel de dados de voz.'
      },
      {
        type: 'paragraph',
        title: 'Qual problema relacionado a ruido em voz voce considera mais importante resolver?',
        helpText: 'Resposta aberta.',
        required: false,
        projectUse: 'revelar cenarios nao previstos e orientar a selecao final de ruidos, exemplos e limitacoes discutidas no relatorio.'
      }
    ]
  }
];

function criarQuestionarioExtensionista() {
  const form = FormApp.create(FORM_CONFIG.title);
  form
    .setDescription(FORM_CONFIG.description)
    .setCollectEmail(FORM_CONFIG.collectEmail)
    .setAllowResponseEdits(FORM_CONFIG.allowResponseEdits)
    .setLimitOneResponsePerUser(FORM_CONFIG.limitOneResponsePerUser)
    .setProgressBar(true)
    .setShowLinkToRespondAgain(false);

  const sheet = SpreadsheetApp.create(FORM_CONFIG.destinationSpreadsheetName);
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());

  FORM_BLOCKS.forEach(function(block) {
    form.addPageBreakItem().setTitle(block.title);
    block.questions.forEach(function(question) {
      if (question.enabled === false) {
        return;
      }
      addQuestion(form, question);
    });
  });

  Logger.log('Formulario de edicao: ' + form.getEditUrl());
  Logger.log('Formulario para respondentes: ' + form.getPublishedUrl());
  Logger.log('Planilha de respostas: ' + sheet.getUrl());
}

function addQuestion(form, question) {
  if (question.type === 'checkbox') {
    addCheckboxQuestion(form, question);
  } else if (question.type === 'multipleChoice') {
    addMultipleChoiceQuestion(form, question);
  } else if (question.type === 'scale') {
    addScaleQuestion(form, question);
  } else if (question.type === 'paragraph') {
    addParagraphQuestion(form, question);
  } else if (question.type === 'audioComparison') {
    addAudioComparisonBlock(form, question);
  } else {
    throw new Error('Tipo de pergunta nao suportado: ' + question.type);
  }
}

function addCheckboxQuestion(form, question) {
  const item = form.addCheckboxItem();
  item
    .setTitle(question.title)
    .setHelpText(withProjectUse(question))
    .setChoiceValues(question.options)
    .setRequired(Boolean(question.required));

  if (question.other) {
    item.showOtherOption(true);
  }

  if (question.maxChoices) {
    const validation = FormApp.createCheckboxValidation()
      .requireSelectAtMost(question.maxChoices)
      .build();
    item.setValidation(validation);
  }
}

function addMultipleChoiceQuestion(form, question) {
  const item = form.addMultipleChoiceItem();
  const options = question.optionsFromAudio ? methodOptionsFromAudio() : question.options;

  item
    .setTitle(question.title)
    .setHelpText(withProjectUse(question))
    .setChoiceValues(options.length ? options : question.fallbackOptions)
    .setRequired(Boolean(question.required));

  if (question.other) {
    item.showOtherOption(true);
  }
}

function addScaleQuestion(form, question) {
  form.addScaleItem()
    .setTitle(question.title)
    .setHelpText(withProjectUse(question))
    .setBounds(1, 5)
    .setLabels(question.leftLabel, question.rightLabel)
    .setRequired(Boolean(question.required));
}

function addParagraphQuestion(form, question) {
  form.addParagraphTextItem()
    .setTitle(question.title)
    .setHelpText(withProjectUse(question))
    .setRequired(Boolean(question.required));
}

function addAudioComparisonBlock(form, question) {
  const filledEntries = AUDIO_COMPARISON_URLS.filter(function(entry) {
    return entry.url && entry.url.trim();
  });

  form.addSectionHeaderItem()
    .setTitle(question.title)
    .setHelpText(buildAudioHelpText(question.helpText, filledEntries));

  filledEntries.forEach(function(entry) {
    if (isYouTubeUrl(entry.url)) {
      form.addVideoItem()
        .setTitle(entry.label)
        .setHelpText(entry.note || '')
        .setVideoUrl(entry.url);
    }
  });
}

function buildAudioHelpText(intro, entries) {
  if (!entries.length) {
    return [
      intro,
      '',
      'Nenhum link de audio foi preenchido em AUDIO_COMPARISON_URLS.',
      'Preencha URLs do Mote ou Google Drive para exibir links nesta secao, ou URLs do YouTube para criar players de video no proprio Forms.',
      'Com Mote, o audio so toca dentro do formulario se o respondente tiver a extensao instalada; sem ela, o link abre o audio no site do Mote.'
    ].join('\n');
  }

  const lines = [intro, ''];
  lines.push('Observacao: links do Mote podem tocar dentro do formulario para quem tiver a extensao Mote instalada. Sem a extensao, o respondente deve abrir o link no site do Mote.');
  lines.push('');
  lines.push('Links dos exemplos:');
  entries.forEach(function(entry) {
    lines.push('- ' + entry.label + ': ' + entry.url);
  });
  return lines.join('\n');
}

function methodOptionsFromAudio() {
  const choices = AUDIO_COMPARISON_URLS
    .filter(function(entry) {
      return Boolean(entry.methodChoice);
    })
    .map(function(entry) {
      return entry.methodChoice;
    });

  choices.push('Nao sei avaliar sem ouvir mais exemplos');
  return unique(choices);
}

function withProjectUse(question) {
  const parts = [];
  if (question.helpText) {
    parts.push(question.helpText);
  }
  if (question.projectUse) {
    parts.push('Uso esperado no projeto: ' + question.projectUse);
  }
  return parts.join('\n\n');
}

function isYouTubeUrl(url) {
  return /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\//i.test(url);
}

function unique(values) {
  const seen = {};
  return values.filter(function(value) {
    if (seen[value]) {
      return false;
    }
    seen[value] = true;
    return true;
  });
}
