/* Instrumento exploratório PTC3528. Não inserir credenciais ou chaves privadas neste arquivo.
   backend.url fica vazio até termos armazenamento privado com recibo verificável.
   Identidades dos métodos estão em manifesto PRIVADO, fora do repositório.
*/
window.VOICE_CONTROL_PERCEPTUAL = Object.freeze({
  studyId: "ptc3528-w261-perceptual-20261117",
  schemaVersion: "1.0.0",
  storagePrefix: "voice-control-perceptual-w261-v1",
  backend: {
    url: "https://jcmceskyxupmzmgqpvvc.supabase.co/functions/v1/ptc3528-perceptual",
    method: "POST",
    // O backend deverá confirmar JSON {ok:true,receiptId:string,receivedAt:string}
    // e autenticar tokens de convite no servidor; ausência de resposta !== sucesso.
    enabled: true
  },
  people: [
    {id:"augusto", name:"Augusto"},
    {id:"gabriel",name:"Gabriel"},
    {id:"lucas", name:"Lucas"}
  ],
  scenes: [
    {id:"c01",title:"Trecho 01 · Abertura",timeLabel:"00:38–00:54",warning:"Trecho escolhido por energia em frequências graves. Ainda não há identificação humana do ruído. Ouça cada alternativa antes de responder.",files:["media/c01_s01.wav","media/c01_s02.wav","media/c01_s03.wav"]},
    {id:"c02",title:"Trecho 02 · Interferência",timeLabel:"02:30–02:46",warning:"Neste trecho, não foi possível igualar totalmente os volumes sem aumentar demais o pico. Evite concluir que o som mais alto é o melhor.",files:["media/c02_s01.wav","media/c02_s02.wav","media/c02_s03.wav"]},
    {id:"c03",title:"Trecho 03 · Encerramento",timeLabel:"05:56–06:12",warning:"Último intervalo. Considere se o processamento preserva a fala enquanto modifica sons do ambiente.",files:["media/c03_s01.wav","media/c03_s02.wav","media/c03_s03.wav"]}
  ],
  rubrics:[
    {key:"intelligibility",title:"Qual torna as palavras mais fáceis de entender?",hint:"Inteligibilidade percebida, não simplesmente volume."},
    {key:"naturalness",title:"Qual mantém a voz mais natural?",hint:"Menos metalização, robótica ou cortes na voz."},
    {key:"noise",title:"Em qual o ruído atrapalha menos a fala?",hint:"Considere o ruído concomitante à voz, não apenas as pausas."},
    {key:"preferred",title:"Qual você usaria em uma reunião on-line?",hint:"Escolha geral considerando fala, ruído e naturalidade."}
  ]
});
