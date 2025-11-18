import { createApp, h, reactive, readonly } from 'vue'

type Toast = { id: number; text: string }

const toasts = reactive<Toast[]>([])
let nextId = 1
let mounted = false

function mountContainer() {
  if (typeof document === 'undefined' || mounted) return

  const container = document.createElement('div')
  container.id = 'vue-toast-root'
  document.body.appendChild(container)

  const ToastApp = {
    setup() {
      return () =>
        h(
          'div',
          {
            style: {
              position: 'fixed',
              bottom: '20px',
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 3000,
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            },
          },
          toasts.map((t) =>
            h(
              'div',
              {
                key: t.id,
                style: {
                  background: 'rgba(0,0,0,0.75)',
                  color: '#fff',
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  fontSize: '0.95rem',
                },
              },
              t.text
            )
          )
        )
    },
  }

  createApp(ToastApp).mount(container)
  mounted = true
}

export function useToast(): {
  toasts: Readonly<Toast[]>
  showToast: (text: string, duration?: number) => void
} {
  // ensure container is mounted when composable is used in browser
  if (typeof window !== 'undefined') {
    mountContainer()
  }

  function showToast(text: string, duration = 3000) {
    const id = nextId++
    toasts.push({ id, text })
    setTimeout(() => {
      const idx = toasts.findIndex((t) => t.id === id)
      if (idx >= 0) toasts.splice(idx, 1)
    }, duration)
  }

  return {
    toasts: readonly(toasts) as Readonly<Toast[]>,
    showToast,
  }
}
