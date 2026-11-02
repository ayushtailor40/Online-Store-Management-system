from database.db import query_db, execute_insert, execute_update


def get_all_categories(search=None, active_only=False):
    """
    Returns list of categories with product counts.
    Supports optional search filter and active-only flag.
    """
    params = []
    where_clauses = []

    if active_only:
        where_clauses.append("c.is_active = 1")
    
    if search:
        where_clauses.append("(c.name LIKE %s OR c.description LIKE %s)")
        search_term = f"%{search.strip()}%"
        params.extend([search_term, search_term])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        SELECT 
            c.id, 
            c.name, 
            c.description, 
            c.is_active, 
            c.created_at, 
            c.updated_at,
            COUNT(p.id) AS product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id AND p.is_active = 1
        {where_sql}
        GROUP BY c.id, c.name, c.description, c.is_active, c.created_at, c.updated_at
        ORDER BY c.name ASC
    """
    return query_db(query, tuple(params))


def get_category_by_id(category_id):
    """Fetches category details by ID along with product count."""
    query = """
        SELECT 
            c.id, 
            c.name, 
            c.description, 
            c.is_active, 
            c.created_at, 
            c.updated_at,
            COUNT(p.id) AS product_count
        FROM categories c
        LEFT JOIN products p ON c.id = p.category_id
        WHERE c.id = %s
        GROUP BY c.id, c.name, c.description, c.is_active, c.created_at, c.updated_at
    """
    return query_db(query, (category_id,), one=True)


def create_category(name, description=""):
    """
    Creates a new product category.
    Validates name uniqueness.
    """
    name = (name or "").strip()
    if not name:
        return False, "Category name cannot be empty."

    # Check for duplicate category name
    existing = query_db("SELECT id FROM categories WHERE LOWER(name) = LOWER(%s)", (name,), one=True)
    if existing:
        return False, f"A category named '{name}' already exists."

    cat_id = execute_insert(
        "INSERT INTO categories (name, description, is_active) VALUES (%s, %s, 1)",
        (name, (description or "").strip())
    )
    return True, cat_id


def update_category(category_id, name, description="", is_active=1):
    """Updates category details with uniqueness verification."""
    name = (name or "").strip()
    if not name:
        return False, "Category name cannot be empty."

    # Check for duplicate name in other categories
    existing = query_db(
        "SELECT id FROM categories WHERE LOWER(name) = LOWER(%s) AND id != %s", 
        (name, category_id), 
        one=True
    )
    if existing:
        return False, f"Another category named '{name}' already exists."

    execute_update(
        "UPDATE categories SET name = %s, description = %s, is_active = %s WHERE id = %s",
        (name, (description or "").strip(), int(is_active), category_id)
    )
    return True, "Category updated successfully."


def delete_category(category_id):
    """
    Safely deletes a category.
    Blocks deletion if any products belong to this category to maintain referential integrity.
    """
    product_count = query_db(
        "SELECT COUNT(*) as count FROM products WHERE category_id = %s",
        (category_id,),
        one=True
    )
    if product_count and product_count['count'] > 0:
        count = product_count['count']
        return False, f"Cannot delete category: {count} product(s) are assigned to it. Please reassign or delete the products first, or archive the category."

    execute_update("DELETE FROM categories WHERE id = %s", (category_id,))
    return True, "Category deleted successfully."
