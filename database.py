import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD",
    "database": "YOUR_DB_NAME",
    "port": 3306
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def search_flights(date_str, origin_city, destination_city):
    query = """
        SELECT
          f.id_flight AS flight_id,
          f.departure_time,
          ADDTIME(f.departure_time, r.duration) AS arrival_time,
          a_from.city AS origin,
          a_to.city AS destination,
          MIN(fp.price) AS min_price
        FROM flights f
        JOIN routes r
          ON r.id_route = f.id_route
        JOIN airports a_from
          ON a_from.airport_code = r.origin_code
        JOIN airports a_to
          ON a_to.airport_code = r.destination_code
        JOIN flight_pricing fp
          ON fp.id_flight = f.id_flight
        WHERE f.flight_status = 'active'
          AND DATE(f.departure_time) = %s
          AND a_from.city = %s
          AND a_to.city = %s
        GROUP BY
          f.id_flight, f.departure_time, r.duration, a_from.city, a_to.city
        ORDER BY f.departure_time
    """

    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (date_str, origin_city, destination_city))
        return cur.fetchall()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def user_login(email, password):
    query = """
        SELECT c.email, c.first_name_eng
        FROM customers c
        JOIN registered_customers r
          ON r.customers_email = c.email
        WHERE c.email = %s
          AND r.password = %s
        LIMIT 1
    """

    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (email, password))
        return cur.fetchone()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def email_exists(email):
    query = "SELECT 1 FROM customers WHERE email = %s LIMIT 1"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, (email,))
        return cur.fetchone() is not None
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def passport_exists(passport):
    query = "SELECT 1 FROM registered_customers WHERE passport = %s LIMIT 1"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, (passport,))
        return cur.fetchone() is not None
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def create_account(email, first_name_eng, last_name_eng, birth_date, passport, password, phone_numbers):
    conn = get_connection()
    try:
        cur = conn.cursor()

        # customers
        cur.execute(
            "INSERT INTO customers (email, first_name_eng, last_name_eng) VALUES (%s, %s, %s)",
            (email, first_name_eng, last_name_eng)
        )

        # registered_customers
        cur.execute(
            """
            INSERT INTO registered_customers
              (customers_email, password, birth_date, passport, registration_date)
            VALUES (%s, %s, %s, %s, CURDATE())
            """,
            (email, password, birth_date, passport)
        )

        # phone_numbers (many)
        cur.executemany(
            "INSERT INTO phone_numbers (customers_email, phone_number) VALUES (%s, %s)",
            [(email, phone) for phone in phone_numbers]
        )

        conn.commit()

    except Error:
        conn.rollback()
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def manager_login(id_worker, password):
    query = """
        SELECT m.id_worker, m.first_name
        FROM managers m
        WHERE m.id_worker = %s
            AND m.password = %s
        LIMIT 1
    """

    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (id_worker, password))
        return cur.fetchone()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def airplane_dimensions(id_flight):
    query = """ 
            SELECT c_eco.num_rows AS economy_rows,
                   c_eco.num_cols AS economy_cols,
                   c_bus.num_rows AS business_rows, 
                   c_bus.num_cols AS business_cols
        
            FROM flights f  
            LEFT JOIN classes c_eco
                ON f.id_plane = c_eco.id_plane AND c_eco.class_type = 'Economy'
            LEFT JOIN classes c_bus
                ON f.id_plane = c_bus.id_plane AND c_bus.class_type = 'Business'
            WHERE f.id_flight = %s
            """
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (id_flight,))
        return cur.fetchone()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

def chosen_flight_details(id_flight):
    query=""" SELECT 
    f.id_flight AS flight_id,
    f.departure_time,
    ADDTIME(f.departure_time, r.duration) as arrival_time,
    airport_from.city AS origin,
    airport_to.city AS destination
    FROM flights f
    JOIN routes r 
        ON r.id_route = f.id_route
    JOIN airports airport_from
        ON airport_from.airport_code = r.origin_code
    JOIN airports airport_to
        ON airport_to.airport_code = r.destination_code
    WHERE f.id_flight = %s
    """
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, (id_flight,))
        return cur.fetchone()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

# בתוך קובץ DB.py
# (ודא שאתה מייבא את datetime למעלה: from datetime import datetime, timedelta)

def get_user_bookings(email, booking_id=None):
    conn = get_connection() # שימוש בפונקציה הפנימית שכבר קיימת לך ב-DB
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT b.id_booking, b.booking_date, b.status AS booking_status, b.total_price,
               t.passenger_name, t.passenger_passport, t.row_number, t.seat_letter, t.class_type,
               f.departure_time, f.flight_status,
               r.origin, r.destination
        FROM bookings b
        JOIN tickets t ON b.id_booking = t.id_booking
        JOIN flights f ON t.id_flight = f.id_flight
        JOIN routes r ON f.id_route = r.id_route
        WHERE (b.customers_email = %s OR b.registered_email = %s)
    """
    params = [email, email]

    if booking_id:
        query += " AND b.id_booking = %s"
        params.append(booking_id)

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # עיבוד הנתונים
    bookings_dict = {}
    for row in results:
        bid = row['id_booking']
        if bid not in bookings_dict:
            bookings_dict[bid] = {
                'info': row,
                'tickets': []
            }
        bookings_dict[bid]['tickets'].append({
            'name': row['passenger_name'],
            'passport': row['passenger_passport'],
            'seat': f"{row['row_number']}{row['seat_letter']}",
            'class': row['class_type']
        })
        
    return bookings_dict

def cancel_booking_in_db(booking_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # בדיקת זמן הטיסה
    cursor.execute("""
        SELECT f.departure_time, b.total_price 
        FROM bookings b 
        JOIN tickets t ON b.id_booking = t.id_booking 
        JOIN flights f ON t.id_flight = f.id_flight 
        WHERE b.id_booking = %s LIMIT 1
    """, (booking_id,))
    
    flight = cursor.fetchone()
    message = ""
    success = False
    
    if flight:
        flight_time = flight['departure_time']
        if isinstance(flight_time, str):
            flight_time = datetime.strptime(flight_time, '%Y-%m-%d %H:%M:%S')

        time_diff = flight_time - datetime.now()

        if time_diff > timedelta(hours=36):
            new_price = float(flight['total_price']) * 0.05
            cursor.execute("""
                UPDATE bookings 
                SET status = 'Cancelled_Client', total_price = %s 
                WHERE id_booking = %s
            """, (new_price, booking_id))
            conn.commit()
            message = f"Order {booking_id} cancelled. 5% fee charged: {new_price} ILS."
            success = True
        else:
            message = "Cannot cancel: Flight is in less than 36 hours."
    else:
        message = "Booking not found."

    cursor.close()
    conn.close()
    return success, message
