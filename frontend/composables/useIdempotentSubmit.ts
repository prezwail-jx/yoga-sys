import { readonly, ref } from "vue"

export function useIdempotentSubmit() {
  const pending = ref(false)
  const activeSignature = ref<string | null>(null)
  const activeKey = ref<string | null>(null)

  async function submit<T>(signature: string, action: (idempotencyKey: string) => Promise<T>): Promise<T> {
    if (pending.value) throw new Error("操作正在处理中")
    if (activeSignature.value !== signature || !activeKey.value) {
      activeSignature.value = signature
      activeKey.value = crypto.randomUUID()
    }
    pending.value = true
    try {
      return await action(activeKey.value)
    } finally {
      pending.value = false
    }
  }

  function reset() {
    activeSignature.value = null
    activeKey.value = null
  }

  return { pending: readonly(pending), submit, reset }
}
