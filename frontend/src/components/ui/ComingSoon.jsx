// Marks a feature from the design that the backend doesn't support yet.
function ComingSoon({ label = 'Coming soon' }) {
  return <span className="soon-badge">{label}</span>
}

export default ComingSoon
