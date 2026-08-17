type CorvusBrandProps = {
  compact?: boolean
}

export function CorvusBrand({ compact = false }: CorvusBrandProps) {
  return (
    <div className={compact ? 'corvus-brand corvus-brand--compact' : 'corvus-brand'}>
      <span className="corvus-mark" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      <span className="corvus-wordmark">Corvus</span>
    </div>
  )
}
