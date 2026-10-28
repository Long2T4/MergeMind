function StatCard({ label, value, sub, tone, children }) {
  return (
    <div className="card stat-card">
      <span className="stat-card-label">{label}</span>
      <span className={`stat-card-value ${tone ? `tone-${tone}` : ''}`}>{value ?? '—'}</span>
      {sub && <span className="stat-card-sub">{sub}</span>}
      {children}
    </div>
  )
}

export default StatCard
