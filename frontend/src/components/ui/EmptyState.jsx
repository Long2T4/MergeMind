function EmptyState({ title, children, action }) {
  return (
    <div className="empty-state">
      <p className="empty-state-title">{title}</p>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

export default EmptyState
