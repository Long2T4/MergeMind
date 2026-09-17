const CATEGORY_LABELS = {
  security: 'Security',
  testing: 'Testing',
  error_handling: 'Error Handling',
  input_validation: 'Input Validation',
  database: 'Database',
  performance: 'Performance',
  code_quality: 'Code Quality',
  logic: 'Logic',
}

function CategoryBadge({ category }) {
  const label = CATEGORY_LABELS[category] || category

  return <span className="category-badge">{label}</span>
}

export default CategoryBadge
