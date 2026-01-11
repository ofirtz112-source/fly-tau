import mysql.connector
from datetime import datetime, timedelta

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            try:
                cls._instance.connection = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="Vika2000!",
                    database="flytauchecking",
                    port=3306
                )
                print("✅ Connected to 'flytau' database (Singleton)")
            except mysql.connector.Error as err:
                print(f"❌ Connection Error: {err}")
                cls._instance.connection = None
        return cls._instance

    # --- פונקציות העבודה (נשארות אותו דבר, משתמשות ב-self.connection) ---

    def get_customer_bookings(self, email):
        """שליפת כל ההזמנות ללקוח רשום"""
        query = """
            SELECT b.id_booking, b.booking_date, b.status as booking_status, b.total_price,
                   f.id_flight, f.departure_time, r.origin_code, a1.city as origin_city,
                   r.destination_code, a2.city as destination_city,
                   t.passenger_name, t.passenger_passport, t.seat_letter, t.row_number, t.class_type
            FROM bookings b
            JOIN tickets t ON b.id_booking = t.id_booking
            JOIN flights f ON t.id_flight = f.id_flight
            JOIN routes r ON f.id_route = r.id_route
            JOIN airports a1 ON r.origin_code = a1.airport_code
            JOIN airports a2 ON r.destination_code = a2.airport_code
            WHERE b.customers_email = %s ORDER BY f.departure_time DESC
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query, (email,))
        res = cursor.fetchall()
        cursor.close()
        return res

    def get_single_booking(self, email, booking_id):
        query = """
            SELECT b.id_booking, b.status as booking_status, b.total_price,
                   f.departure_time, a1.city as origin_city, a2.city as destination_city,
                   t.passenger_name, t.seat_letter, t.row_number, t.class_type
            FROM bookings b
            JOIN tickets t ON b.id_booking = t.id_booking
            JOIN flights f ON t.id_flight = f.id_flight
            JOIN routes r ON f.id_route = r.id_route
            JOIN airports a1 ON r.origin_code = a1.airport_code
            JOIN airports a2 ON r.destination_code = a2.airport_code
            WHERE b.customers_email = %s AND b.id_booking = %s
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query, (email, booking_id))
        res = cursor.fetchall()
        cursor.close()
        return res

    def get_booking_details_for_cancellation(self, booking_id):
        # העתקנו את השאילתה בדיוק מתוך main.py כדי לשמור על הלוגיקה
        query = """
            SELECT f.departure_time, b.total_price, b.status 
            FROM bookings b 
            JOIN tickets t ON b.id_booking = t.id_booking 
            JOIN flights f ON t.id_flight = f.id_flight 
            WHERE b.id_booking = %s 
            LIMIT 1
        """
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, (booking_id,))
            return cursor.fetchone()  # מחזיר תוצאה אחת או None
        finally:
            cursor.close()

    def user_login(self, email, password):
        # השאילתה המעודכנת עם JOIN
        query = """
            SELECT c.email, c.first_name_eng 
            FROM customers c
            JOIN registered_customers rc ON c.email = rc.customers_email
            WHERE c.email = %s AND rc.password = %s
        """
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, (email, password))
            result = cursor.fetchone()
            return result
        finally:
            cursor.close()

    # (כאן יכולות לבוא שאר הפונקציות כמו update_booking_status וכו')
    def manager_login(self, id_worker, password):
        query = "SELECT id_worker, first_name FROM managers WHERE id_worker = %s AND password = %s"
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query, (id_worker, password))
        result = cursor.fetchone()
        cursor.close()
        return result

    def email_exists(self, email):
        cursor = self.connection.cursor()
        cursor.execute("SELECT email FROM customers WHERE email = %s", (email,))
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists

    def passport_exists(self, passport):
        cursor = self.connection.cursor()
        # תיקון: מחפשים בטבלת registered_customers ובעמודה passport
        cursor.execute("SELECT passport FROM registered_customers WHERE passport = %s", (passport,))
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists

    def create_account(self, email, first_name, last_name, birth_date, passport, password, phone_numbers):
        print("--- RUNNING NEW CREATE ACCOUNT FUNCTION ---")  # <--- תוסיפי את זה לבדיקה
        cursor = self.connection.cursor()
        try:
            # --- שלב 1: ניסיון ליצור לקוח בסיסי ---
            # אם הלקוח חדש לגמרי - זה יעבוד.
            # אם הלקוח היה אורח בעבר - זה יזרוק שגיאה כי האימייל תפוס.
            cursor.execute("""
                INSERT INTO customers (email, first_name_eng, last_name_eng)
                VALUES (%s, %s, %s)
            """, (email, first_name, last_name))

            # --- שלב 2: יצירת החשבון הרשום (הפרטים החסויים) ---
            # תיקון: שימוש ב-passport במקום passport_number
            cursor.execute("""
                INSERT INTO registered_customers (customers_email, password, birth_date, passport, registration_date)
                VALUES (%s, %s, %s, %s, CURDATE())
            """, (email, password, birth_date, passport))

            # --- שלב 3: טלפונים ---
            for phone in phone_numbers:
                if phone.strip():
                    cursor.execute("""
                        INSERT INTO phone_numbers (phone_number, customers_email)
                        VALUES (%s, %s)
                    """, (phone, email))

            self.connection.commit()

        except Exception as e:
            self.connection.rollback()

            # --- הטיפול במקרה של אורח לשעבר ---
            if "Duplicate entry" in str(e) and "customers.PRIMARY" in str(e):
                try:
                    print(f"User {email} already exists inside 'customers', upgrading to registered...")

                    # 1. עדכון שמות למקרה שהשתנו
                    cursor.execute("""
                        UPDATE customers SET first_name_eng=%s, last_name_eng=%s WHERE email=%s
                    """, (first_name, last_name, email))

                    # 2. הוספה לטבלת הרשומים בלבד
                    cursor.execute("""
                        INSERT INTO registered_customers (customers_email, password, birth_date, passport, registration_date)
                        VALUES (%s, %s, %s, %s, CURDATE())
                    """, (email, password, birth_date, passport))

                    # 3. הוספת טלפונים (עם IGNORE למקרה שכבר קיימים)
                    for phone in phone_numbers:
                        if phone.strip():
                            cursor.execute("""
                                INSERT IGNORE INTO phone_numbers (phone_number, customers_email)
                                VALUES (%s, %s)
                            """, (phone, email))

                    self.connection.commit()
                    return  # הצלחה!

                except Exception as inner_e:
                    self.connection.rollback()
                    raise inner_e
            else:
                raise e
        finally:
            cursor.close()

    # --- פונקציות חיפוש טיסות ---

    def get_all_destinations(self):
        query = "SELECT DISTINCT city, country, airport_name FROM airports ORDER BY city"
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()
        return res

    def get_flight_data(self, date_str=None, origin=None, destination=None, flight_id=None):
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT f.id_flight, 
                   f.departure_time, 
                   -- התיקון כאן: מחשבים את זמן ההגעה במקום לשלוף שדה שלא קיים
                   ADDTIME(f.departure_time, r.duration) AS arrival_time, 
                   f.flight_status,
                   a1.city as origin, 
                   a2.city as destination,
                   MIN(p.price) as min_price
            FROM flights f
            JOIN routes r ON f.id_route = r.id_route
            JOIN airports a1 ON r.origin_code = a1.airport_code
            JOIN airports a2 ON r.destination_code = a2.airport_code
            JOIN flight_pricing p ON f.id_flight = p.id_flight
        """
        params = []
        conditions = []
        if flight_id:
            conditions.append("f.id_flight = %s")
            params.append(flight_id)
        if date_str:
            conditions.append("DATE(f.departure_time) = %s")
            params.append(date_str)
        if origin:
            conditions.append("a1.city = %s")
            params.append(origin)
        if destination:
            conditions.append("a2.city = %s")
            params.append(destination)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " GROUP BY f.id_flight"

        cursor.execute(query, params)
        res = cursor.fetchall()
        cursor.close()
        return res

    # --- פונקציות ניהול הזמנות (כאן התיקון ל-self.connection) ---

    def get_customer_bookings(self, email):
        """שליפת הזמנות ללקוח רשום בלבד (לפי registered_email)"""
        query = """
            SELECT 
                b.id_booking, b.booking_date, b.status as booking_status, b.total_price,
                f.id_flight, f.departure_time,
                r.origin_code, a1.city as origin_city,
                r.destination_code, a2.city as destination_city,
                t.passenger_name, t.passenger_passport, t.seat_letter, t.row_number, t.class_type
            FROM bookings b
            JOIN tickets t ON b.id_booking = t.id_booking
            JOIN flights f ON t.id_flight = f.id_flight
            JOIN routes r ON f.id_route = r.id_route
            JOIN airports a1 ON r.origin_code = a1.airport_code
            JOIN airports a2 ON r.destination_code = a2.airport_code
            -- השינוי הוא כאן: מחפשים לפי registered_email בלבד
            WHERE b.registered_email = %s
            ORDER BY f.departure_time DESC
        """
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, (email,))
            return cursor.fetchall()
        finally:
            cursor.close()



    def update_booking_status(self, booking_id, new_status, new_price):
        query = "UPDATE bookings SET status = %s, total_price = %s WHERE id_booking = %s"
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (new_status, new_price, booking_id))
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            return False
        finally:
            cursor.close()

    # --- פונקציות מנהל ---

    def get_all_flights_for_manager(self):
        query = """
            SELECT 
                f.id_flight, 
                f.departure_time, 
                ADDTIME(f.departure_time, r.duration) as landing_time,  -- חישוב זמן נחיתה
                f.flight_status,
                r.origin_code, 
                air_origin.country as origin_country, -- שם מדינת מוצא
                r.destination_code, 
                air_dest.country as destination_country, -- שם מדינת יעד
                p.id_plane, 
                p.size as plane_size,
                (SELECT COUNT(*) FROM tickets t WHERE t.id_flight = f.id_flight) as passenger_count
            FROM flights f
            JOIN routes r ON f.id_route = r.id_route
            JOIN planes p ON f.id_plane = p.id_plane
            JOIN airports air_origin ON r.origin_code = air_origin.airport_code
            JOIN airports air_dest ON r.destination_code = air_dest.airport_code
            ORDER BY f.departure_time DESC
        """
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()
        return res

    def get_flight_crew_names(self, flight_id):
        """שולף שמות מלאים של הצוות המשובץ לטיסה"""
        # משתמשים בחיבור הקיים של המחלקה
        cursor = self.connection.cursor(dictionary=True)

        try:
            # שליפת שמות טייסים (שם מלא)
            cursor.execute("""
                SELECT CONCAT(first_name, ' ', last_name) AS full_name 
                FROM pilots p
                JOIN pilots_in_flights pif ON p.id_worker = pif.id_worker
                WHERE pif.id_flight = %s""", (flight_id,))
            pilots = [row['full_name'] for row in cursor.fetchall()]

            # שליפת שמות דיילים (שם מלא)
            cursor.execute("""
                SELECT CONCAT(first_name, ' ', last_name) AS full_name 
                FROM flight_attendants fa
                JOIN flight_attendants_in_flights af ON fa.id_worker = af.id_worker
                WHERE af.id_flight = %s""", (flight_id,))
            attendants = [row['full_name'] for row in cursor.fetchall()]

            return {"pilots": pilots, "attendants": attendants}

        except Exception as e:
            print(f"Error getting crew: {e}")
            return {"pilots": [], "attendants": []}

        finally:
            # סוגרים רק את ה-Cursor, לא את החיבור לבסיס הנתונים
            cursor.close()

    def cancel_flight_full_logic(self, flight_id):
        cursor = self.connection.cursor()
        try:
            cursor.execute("UPDATE flights SET flight_status = 'Cancelled' WHERE id_flight = %s", (flight_id,))
            cursor.execute(
                "UPDATE bookings b JOIN tickets t ON b.id_booking = t.id_booking SET b.status = 'Cancelled_System' WHERE t.id_flight = %s",
                (flight_id,))
            self.connection.commit()
            return True, "Flight cancelled successfully."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)
        finally:
            cursor.close()

    def get_routes_only(self):
        """שולף את כל הנתיבים הקיימים למילוי הטופס בדאשבורד"""
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT r.id_route, 
                   r.origin_code, a1.city as origin_city, 
                   r.destination_code, a2.city as destination_city,
                   r.duration
            FROM routes r
            JOIN airports a1 ON r.origin_code = a1.airport_code
            JOIN airports a2 ON r.destination_code = a2.airport_code
        """
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result

    def get_available_resources(self, departure_time_str, route_id):
        """גרסה משופרת: בדיקת זמינות כולל מיקום, הסמכות וחפיפת זמנים"""
        cursor = self.connection.cursor(dictionary=True)
        try:
            # 1. סידור תאריכים
            clean_time_str = departure_time_str.replace('T', ' ')
            if len(clean_time_str) == 16: clean_time_str += ':00'
            dep_time = datetime.strptime(clean_time_str, '%Y-%m-%d %H:%M:%S')

            # 2. הבנת הטיסה החדשה (נתיב, משך וסוג)
            cursor.execute("SELECT origin_code, duration FROM routes WHERE id_route = %s", (route_id,))
            route = cursor.fetchone()
            if not route: return None

            required_origin = route['origin_code']
            duration_str = str(route['duration'])
            h, m, s = map(int, duration_str.split(':'))
            arr_time = dep_time + timedelta(hours=h, minutes=m, seconds=s)

            # חישוב: מעל 360 דקות (6 שעות) נחשב ארוך. 6 שעות בדיוק נחשב קצר.
            total_minutes = (h * 60) + m
            is_long_haul = total_minutes > 360

            # --- 3. בדיקת מטוסים ---
            query_planes = """
                SELECT p.id_plane, p.size,
                COALESCE(
                    (SELECT r_prev.destination_code 
                     FROM flights f_prev 
                     JOIN routes r_prev ON f_prev.id_route = r_prev.id_route
                     WHERE f_prev.id_plane = p.id_plane 
                       AND f_prev.departure_time < %s 
                       AND f_prev.flight_status != 'Cancelled'
                     ORDER BY f_prev.departure_time DESC LIMIT 1
                    ), 'TLV') as current_location,
                (SELECT COUNT(*) FROM flights f
                 JOIN routes r ON f.id_route = r.id_route
                 WHERE f.id_plane = p.id_plane
                   AND (f.departure_time < %s) 
                   AND (ADDTIME(f.departure_time, r.duration) > %s)
                   AND f.flight_status != 'Cancelled'
                ) as busy_count
                FROM planes p
            """
            cursor.execute(query_planes, (dep_time, arr_time, dep_time))
            planes_raw = cursor.fetchall()

            processed_planes = []
            for p in planes_raw:
                is_busy = p['busy_count'] > 0
                loc_ok = (p['current_location'] == required_origin)
                size_ok = not (is_long_haul and p['size'] != 'Large')

                reason = ""
                if is_busy:
                    reason = "Time Overlap (Busy)"
                elif not loc_ok:
                    reason = f"Located in {p['current_location']}"
                elif not size_ok:
                    reason = "Plane too small"

                if not size_ok and is_long_haul: continue

                processed_planes.append({
                    'id_plane': p['id_plane'], 'size': p['size'], 'current_location': p['current_location'],
                    'is_valid': (not is_busy) and loc_ok, 'reason': reason
                })

            # --- 4. בדיקת טייסים ---
            query_pilots = """
                SELECT w.id_worker, w.first_name, w.last_name, w.long_flights,
                COALESCE(
                    (SELECT r_prev.destination_code 
                     FROM flights f_prev 
                     JOIN routes r_prev ON f_prev.id_route = r_prev.id_route
                     JOIN pilots_in_flights pif ON f_prev.id_flight = pif.id_flight
                     WHERE pif.id_worker = w.id_worker
                       AND f_prev.departure_time < %s 
                       AND f_prev.flight_status != 'Cancelled'
                     ORDER BY f_prev.departure_time DESC LIMIT 1
                    ), 'TLV') as current_location,
                (SELECT COUNT(*) FROM pilots_in_flights pf
                 JOIN flights f ON pf.id_flight = f.id_flight
                 JOIN routes r ON f.id_route = r.id_route
                 WHERE pf.id_worker = w.id_worker
                   AND (f.departure_time < %s) 
                   AND (ADDTIME(f.departure_time, r.duration) > %s)
                   AND f.flight_status != 'Cancelled'
                ) as busy_count
                FROM pilots w
            """
            cursor.execute(query_pilots, (dep_time, arr_time, dep_time))
            pilots_raw = cursor.fetchall()

            processed_pilots = []
            for w in pilots_raw:
                is_busy = w['busy_count'] > 0
                loc_ok = (w['current_location'] == required_origin)
                qual_ok = not (is_long_haul and w['long_flights'] == 0)

                reason = ""
                if is_busy:
                    reason = "Time Overlap"
                elif not loc_ok:
                    reason = f"Located in {w['current_location']}"
                elif not qual_ok:
                    reason = "Not Qualified"

                processed_pilots.append({
                    'id_worker': w['id_worker'], 'name': f"{w['first_name']} {w['last_name']}",
                    'qualified_for_long_haul': (w['long_flights'] == 1),
                    'is_valid': (not is_busy) and loc_ok and qual_ok, 'reason': reason
                })

            # --- 5. בדיקת דיילים ---
            query_attendants = """
                SELECT w.id_worker, w.first_name, w.last_name, w.long_flights,
                COALESCE(
                    (SELECT r_prev.destination_code 
                     FROM flights f_prev 
                     JOIN routes r_prev ON f_prev.id_route = r_prev.id_route
                     JOIN flight_attendants_in_flights af ON f_prev.id_flight = af.id_flight
                     WHERE af.id_worker = w.id_worker
                       AND f_prev.departure_time < %s 
                       AND f_prev.flight_status != 'Cancelled'
                     ORDER BY f_prev.departure_time DESC LIMIT 1
                    ), 'TLV') as current_location,
                (SELECT COUNT(*) FROM flight_attendants_in_flights af
                 JOIN flights f ON af.id_flight = f.id_flight
                 JOIN routes r ON f.id_route = r.id_route
                 WHERE af.id_worker = w.id_worker
                   AND (f.departure_time < %s) 
                   AND (ADDTIME(f.departure_time, r.duration) > %s)
                   AND f.flight_status != 'Cancelled'
                ) as busy_count
                FROM flight_attendants w
            """
            cursor.execute(query_attendants, (dep_time, arr_time, dep_time))
            attendants_raw = cursor.fetchall()

            processed_attendants = []
            for w in attendants_raw:
                is_busy = w['busy_count'] > 0
                loc_ok = (w['current_location'] == required_origin)
                qual_ok = not (is_long_haul and w['long_flights'] == 0)

                reason = ""
                if is_busy:
                    reason = "Time Overlap"
                elif not loc_ok:
                    reason = f"Located in {w['current_location']}"
                elif not qual_ok:
                    reason = "Not Qualified"

                processed_attendants.append({
                    'id_worker': w['id_worker'], 'name': f"{w['first_name']} {w['last_name']}",
                    'qualified_for_long_haul': (w['long_flights'] == 1),
                    'is_valid': (not is_busy) and loc_ok and qual_ok, 'reason': reason
                })

# ... זה ההמשך של get_available_resources בתוך ה-loop ...
            return {
                "planes": processed_planes, "pilots": processed_pilots, "attendants": processed_attendants,
                "is_long_haul": is_long_haul, "arrival_time": arr_time.strftime('%Y-%m-%d %H:%M')
            }

        except Exception as e:
            print(f"Error checking availability: {e}")
            return None
        finally:
            cursor.close()  # <--- הוספתי את הסוגריים שהיו חסרים לך!

    def add_new_flight(self, route_id, plane_id, departure_time, pilots_ids, attendants_ids, manager_id, price_eco,
                       price_bus):
        """יצירת טיסה חדשה, שיבוץ צוות וקביעת מחירים"""
        cursor = self.connection.cursor()
        try:
            # 1. יצירת הטיסה
            query_flight = """
                INSERT INTO flights (id_route, id_plane, departure_time, flight_status, managers_id_worker)
                VALUES (%s, %s, %s, 'Scheduled', %s)
            """
            cursor.execute(query_flight, (route_id, plane_id, departure_time, manager_id))
            new_flight_id = cursor.lastrowid

            # 2. שיבוץ טייסים
            query_pilots = "INSERT INTO pilots_in_flights (id_worker, id_flight) VALUES (%s, %s)"
            for pid in pilots_ids:
                cursor.execute(query_pilots, (pid, new_flight_id))

            # 3. שיבוץ דיילים
            query_attendants = "INSERT INTO flight_attendants_in_flights (id_worker, id_flight) VALUES (%s, %s)"
            for aid in attendants_ids:
                cursor.execute(query_attendants, (aid, new_flight_id))

            # 4. יצירת רשומת מחיר - Economy (תמיד קיים)
            cursor.execute(
                "INSERT INTO flight_pricing (id_flight, price, class_type) VALUES (%s, %s, 'Economy')",
                (new_flight_id, price_eco))

            # 5. יצירת רשומת מחיר - Business (רק אם הוזן מחיר)
            if price_bus and str(price_bus).strip():
                cursor.execute(
                    "INSERT INTO flight_pricing (id_flight, price, class_type) VALUES (%s, %s, 'Business')",
                    (new_flight_id, price_bus))

            self.connection.commit()
            return True, "Flight created successfully"
        except Exception as e:
            self.connection.rollback()
            return False, str(e)
        finally:
            cursor.close()

    def get_nearest_flight_date(self, origin, dest, target_date, after=False):
        """מוצא את תאריך הטיסה הקרוב ביותר בנתיב מסוים"""
        # הגדרת אופרטור וסדר מיון לפי האם אנחנו מחפשים לפני או אחרי התאריך
        operator = ">=" if after else "!="
        order_clause = "f.departure_time ASC" if after else f"ABS(DATEDIFF(f.departure_time, %s)) ASC"

        query = f"""
            SELECT DATE(f.departure_time) as flight_date
            FROM flights f
            JOIN routes r ON f.id_route = r.id_route
            JOIN airports a1 ON r.origin_code = a1.airport_code
            JOIN airports a2 ON r.destination_code = a2.airport_code
            WHERE a1.city = %s AND a2.city = %s 
            AND f.flight_status != 'Cancelled'
            AND DATE(f.departure_time) {operator} %s
            ORDER BY {order_clause} LIMIT 1
        """

        cursor = self.connection.cursor(dictionary=True)
        try:
            # אם זה לא 'after', אנחנו צריכים להעביר את target_date פעמיים (אחד ל-WHERE ואחד ל-ORDER BY)
            if not after:
                cursor.execute(query, (origin, dest, target_date, target_date))
            else:
                cursor.execute(query, (origin, dest, target_date))

            res = cursor.fetchone()
            return res['flight_date'].strftime('%Y-%m-%d') if res else None
        except Exception as e:
            print(f"Error in get_nearest_flight_date: {e}")
            return None
        finally:
            cursor.close()
