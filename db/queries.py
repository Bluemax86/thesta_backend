from .connection import get_db_connection

def get_products_by_type(product_type=None, reservable_only=False):
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
        SELECT p.product_id, p.product_name, p.unit_price, p.fixed_price, p.reservable, p.default_image_url, pt.description
        FROM products p
        JOIN product_types pt ON p.product_type_id = pt.product_type_id
        WHERE 1=1
    """
    params = []
    if product_type:
        query += " AND pt.description = %s"
        params.append(product_type)
    if reservable_only:
        query += " AND p.reservable = true"

    cur.execute(query, params)
    products = cur.fetchall()
    cur.close()
    conn.close()
    return products

def create_reservation(customer_id, product_id, check_in_date, check_out_date, total_cost):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reservations (customer_id, product_id, check_in_date, check_out_date, total_cost, created_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING reservation_id
    """, (customer_id, product_id, check_in_date, check_out_date, total_cost))
    reservation_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return reservation_id

def get_reservation_by_id(reservation_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.reservation_id, c.first_name, c.last_name, p.product_name, r.check_in_date, r.check_out_date, r.total_cost
        FROM reservations r
        JOIN customers c ON r.customer_id = c.customer_id
        JOIN products p ON r.product_id = p.product_id
        WHERE r.reservation_id = %s
    """, (reservation_id,))
    reservation = cur.fetchone()
    cur.close()
    conn.close()
    return reservation

def get_customer_id_by_user_id(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT customer_id FROM customers WHERE user_id = %s", (user_id,))
    customer_id = cur.fetchone()[0]
    cur.close()
    conn.close()
    return customer_id

def create_user(email, password_hash, user_role):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
      cur.execute("""
          INSERT INTO users (email, password_hash, user_role, last_logged_in)
          VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
          RETURNING user_id
      """, (email, password_hash, user_role))
      user_id = cur.fetchone()[0]
      conn.commit()
      return user_id
    except psycopg2.Error as e:
      conn.rollback()
      raise Exception(f"Database error: {str(e)}")
    finally:
      cur.close()
      conn.close()

def create_customer(user_id, first_name, last_name, email, phone):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO customers (user_id, first_name, last_name, email, phone, created_at)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
    """, (user_id, first_name, last_name, email, phone))
    conn.commit()
    cur.close()
    conn.close()

def get_user_by_email(email, user_role):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, password_hash FROM users WHERE email = %s AND user_role = %s", (email, user_role))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def update_last_logged_in(email):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_logged_in = CURRENT_TIMESTAMP WHERE email = %s", (email,))
    conn.commit()
    cur.close()
    conn.close()

def get_reservations():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.reservation_id, c.first_name, c.last_name, p.product_name, r.check_in_date, r.check_out_date, r.total_cost
        FROM reservations r
        JOIN customers c ON r.customer_id = c.customer_id
        JOIN products p ON r.product_id = p.product_id
        ORDER BY r.check_in_date DESC
    """)
    reservations = cur.fetchall()
    cur.close()
    conn.close()
    return reservations

def get_total_reservations():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM reservations")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total

def get_total_revenue():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT SUM(total_cost) FROM reservations")
    total = cur.fetchone()[0] or 0.0
    cur.close()
    conn.close()
    return total

def get_revenue_by_type():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT pt.description, SUM(r.total_cost) as revenue
        FROM reservations r
        JOIN products p ON r.product_id = p.product_id
        JOIN product_types pt ON p.product_type_id = pt.product_type_id
        GROUP BY pt.description
    """)
    revenue = cur.fetchall()
    cur.close()
    conn.close()
    return revenue