export class ActionGuard {
  private readonly pending = new Set<string>()

  isPending(actionId: string): boolean {
    return this.pending.has(actionId)
  }

  async run<T>(actionId: string, action: () => Promise<T>): Promise<T | null> {
    if (this.pending.has(actionId)) return null
    this.pending.add(actionId)
    try {
      return await action()
    } finally {
      this.pending.delete(actionId)
    }
  }
}
