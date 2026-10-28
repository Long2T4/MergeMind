import { categoryLabel } from '../constants/categories'

function CategoryBadge({ category }) {
  return <span className="category-badge">{categoryLabel(category)}</span>
}

export default CategoryBadge
