<template>
  <div class="min-h-screen bg-slate-900 text-white p-6 font-sans">
    <header class="flex justify-between items-center pb-6 border-b border-slate-800 mb-6">
      <h1 class="text-2xl font-bold text-blue-400">🛡️ Painel de Acesso Inteligente</h1>
      <span :class="statusClass" class="px-3 py-1 rounded-full text-xs font-semibold">
        {{ statusText }}
      </span>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- Câmera ao Vivo -->
      <div class="md:col-span-2 bg-slate-800 p-4 rounded-xl border border-slate-700">
        <h2 class="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Câmera ao Vivo</h2>
        <div class="relative aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center border border-slate-900">
          <img v-if="cameraImage" :src="cameraImage" class="w-full h-full object-cover" />
          <p v-else class="text-slate-500 text-sm">Aguardando sinal da câmera/Python...</p>
        </div>
      </div>

      <!-- Leitura da IA -->
      <div class="bg-slate-800 p-4 rounded-xl border border-slate-700 flex flex-col justify-between">
        <div>
          <h2 class="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">Análise em Tempo Real</h2>
          
          <div class="p-4 rounded-lg bg-slate-900/60 border border-slate-700/50 mb-4">
            <p class="text-xs text-slate-400 uppercase tracking-wider mb-1">Status da Predição</p>
            <p class="text-2xl font-black" :class="(iaData?.classe || '').includes('Autorizado') ? 'text-emerald-400' : 'text-rose-400'">
              {{ iaData?.classe || 'Aguardando...' }}
            </p>
          </div>

          <div class="p-4 rounded-lg bg-slate-900/60 border border-slate-700/50">
            <p class="text-xs text-slate-400 uppercase tracking-wider mb-1">Similaridade facial (0–1)</p>
            <p class="text-2xl font-bold text-amber-400">
              {{ iaData?.confianca ?? '—' }}
            </p>
          </div>
        </div>

        <button @click="abrirPortao" class="w-full mt-6 py-3 bg-blue-600 hover:bg-blue-500 active:scale-95 transition-all rounded-lg font-bold shadow-lg">
          🔓 Abrir Portão Manualmente
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const cameraImage = ref('')
const statusText = ref('Desconectado')
const statusClass = ref('bg-rose-500/20 text-rose-400 border border-rose-500/30')
const iaData = ref({ classe: 'Aguardando reconhecimento facial', confianca: null })
const ultimoReconhecimento = ref('')
let socket = null

onMounted(() => {
  socket = new WebSocket('ws://localhost:8000/ws/stream')

  socket.onopen = () => {
    statusText.value = 'Conectado ao Python'
    statusClass.value = 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
  }

  socket.onmessage = (event) => {
  const data = JSON.parse(event.data)

  if (data.image) {
    cameraImage.value = data.image.startsWith('data:')
      ? data.image
      : `data:image/jpeg;base64,${data.image}`
  }

  const acesso = data.acesso
  const resultado = String(data.resultado || '')
  const nomeReconhecido = acesso?.cadastro ||
    resultado.match(/^(?:Autorizado|Reconhecido):\\s*(.+)$/i)?.[1]

  if (nomeReconhecido) {
    ultimoReconhecimento.value = nomeReconhecido
  } else {
    ultimoReconhecimento.value = ''
  }

  const scores = data.identidade?.similaridades || {}
  const evidencias = data.identidade?.evidencias_ativas || []
  const rostoAtivo = evidencias.some(chave => chave.endsWith(':rosto'))

  const valores = rostoAtivo
    ? Object.entries(scores)
        .filter(([chave]) => chave.endsWith(':rosto'))
        .map(([, valor]) => Number(valor))
        .filter(Number.isFinite)
    : []

  iaData.value = {
    classe: acesso?.status === 'autorizado'
      ? `Acesso autorizado: ${acesso.cadastro}`
      : ultimoReconhecimento.value
        ? `Último reconhecimento: ${ultimoReconhecimento.value}`
        : (data.identidade?.evidencias_ativas?.length
            ? 'Reconhecimento em análise'
            : 'Aguardando reconhecimento facial'),
    confianca: valores.length
      ? Math.max(...valores).toFixed(3)
      : null
  }
}

  socket.onclose = () => {
    statusText.value = 'Desconectado'
    statusClass.value = 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
  }
})

onUnmounted(() => {
  if (socket) socket.close()
})

const abrirPortao = () => {
  alert('Sinal enviado ao portão com sucesso!')
}
</script>
