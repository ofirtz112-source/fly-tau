from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import Customer, Manager, Flight, Booking
from database import Database
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'flytau_secret_key'
db = Database()

# --- 1. עמודי לקוח וחיפוש ---

@app.route('/')
def home_page():
    destinations = db.get_all_destinations()

    origin = request.args.get('origin')
    destination = request.args.get('destination')
    date = request.args.get('date')
    return_date = request.args.get('return_date')
    trip_type = request.args.get('trip_type')

    outbound_flights = []
    return_flights = []
    # אתחול המשתנה כדי למנוע שגיאות ב-HTML
    suggested_dates = {"outbound": None, "return": None}
    search_performed = False

    if origin and destination and date:
        search_performed = True
        outbound_flights = Flight.search(date, origin, destination)

        if not outbound_flights:
            suggested_dates["outbound"] = db.get_nearest_flight_date(origin, destination, date)

        if trip_type == 'round' and return_date:
            return_flights = Flight.search(return_date, destination, origin)

            if not return_flights:
                # בודקים אחרי תאריך ההמראה (הלוך)
                base_date = suggested_dates["outbound"] if suggested_dates["outbound"] else date
                suggested_dates["return"] = db.get_nearest_flight_date(destination, origin, base_date, after=True)

    return render_template('home_page.html',
                           destinations=destinations,
                           outbound_flights=outbound_flights,
                           return_flights=return_flights,
                           suggested_dates=suggested_dates,
                           search_performed=search_performed,
                           origin=origin,
                           destination=destination,
                           date=date,
                           return_date=return_date,
                           trip_type=trip_type)


@app.route('/login', methods=['GET', 'POST'])
def register_login_page():
    email = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Customer.login(email, password)
        if user:
            session['user_id'] = user.email
            session['first_name'] = user.first_name
            session['role'] = 'customer'
            session['email'] = user.email
            return redirect(url_for('home_page'))
        flash("Invalid email or password", "danger")
    return render_template('register_login.html', email=email)


@app.route('/register', methods=['GET', 'POST'])
def create_account_page():
    if request.method == 'POST':
        f = request.form

        # שימי לב: אנחנו שולחים את הנתונים למודל (ודאי שה-HTML שלך שולח 'passport_number')
        success, message = Customer.register(
            f.get('email'), f.get('first_name'), f.get('last_name'),
            f.get('date_of_birth'), f.get('passport_number'),
            f.get('password'), request.form.getlist('phone_numbers')
        )

        if success:
            # --- השינוי הגדול: כניסה אוטומטית (Auto-Login) ---
            # במקום לשלוח להתחברות, אנחנו מכניסים את הפרטים ל-SESSION מיד
            session['user_id'] = f.get('email')
            session['first_name'] = f.get('first_name')
            session['role'] = 'customer'
            session['email'] = f.get('email')

            # הודעה מעוצבת ומזמינה
            flash(f"Registration successful! Welcome to FlyTAU, {f.get('first_name')}.", "success")

            # שליחה ישירות לדף הבית
            return redirect(url_for('home_page'))

        return render_template('create_account.html', error=message, **f)
    return render_template('create_account.html')


@app.route('/my-bookings', methods=['GET', 'POST'])
def view_bookings():
    """הצגת הזמנות ללקוח רשום או לאורח - גרסה מעודכנת"""
    now = datetime.now()

    if request.method == 'POST':
        # --- לוגיקה לאורח (Guest) ---
        email = request.form.get('email')
        booking_id = request.form.get('id_booking')

        if not email or not booking_id:
            flash("Please provide both email and booking ID.", "error")
            return render_template('search_bookings.html')

        single_booking = Booking.get_specific_booking(email, booking_id)

        if single_booking:
            # שימוש בפונקציה המרכזית שיצרנו במודל למיון ההזמנה
            # אנחנו שולחים רשימה עם פריט אחד ([single_booking]) כי הפונקציה מצפה לרשימה
            conf, comp, c_you, c_sys = Booking.organize_bookings([single_booking])

            return render_template('bookings_results.html',
                                   confirmed=conf, completed=comp,
                                   cancelled_by_you=c_you, cancelled_by_system=c_sys,
                                   is_guest=True, now=now)
        else:
            flash("No booking found with these details.", "error")
            return render_template('search_bookings.html')

    # --- לוגיקה למשתמש רשום (Registered User) ---
    user_email = session.get('email')
    if user_email:
        # כאן נשארנו עם הלוגיקה המקורית שעובדת עבור משתמש רשום
        conf, comp, c_you, c_sys = Booking.get_user_bookings(user_email)
        return render_template('bookings_results.html',
                               confirmed=conf, completed=comp,
                               cancelled_by_you=c_you, cancelled_by_system=c_sys,
                               is_guest=False, now=now)

    return render_template('search_bookings.html')


@app.route("/cancel-booking", methods=["POST"])
def cancel_booking():
    """ביטול הזמנה ע"י לקוח - הגרסה החדשה והנקייה"""
    booking_id = request.form.get('id_booking')

    # בדיקת קלט בסיסית
    if not booking_id:
        flash("Invalid request.", "error")
        return redirect(url_for('view_bookings'))

    # הקסם קורה כאן: שורה אחת במקום כל הלוגיקה וה-SQL שהיו פה
    success, message = Booking.cancel_by_customer(booking_id)

    # הצגת ההודעה למשתמש (הודעת ההצלחה או הכישלון מגיעה מהמודל)
    flash(message, "success" if success else "error")

    return redirect(url_for('view_bookings'))


@app.route('/manager-login', methods=['GET', 'POST'])
def manager_login_page():
    if request.method == 'POST':
        manager = Manager.login(request.form.get('id_worker'), request.form.get('password'))
        if manager:
            session['user_id'] = manager.id_worker
            session['first_name'] = manager.first_name
            session['role'] = 'manager'
            return redirect(url_for('manager_dashboard'))
        flash("Access Denied: Invalid Credentials", "danger")
    return render_template('manager_login.html')


@app.route('/manager/dashboard')
def manager_dashboard():
    # בדיקת הרשאות (נשאר אותו דבר)
    if session.get('role') != 'manager':
        return redirect(url_for('manager_login_page'))

    # הקסם החדש: שורה אחת שמביאה את הכל מוכן מהמודל!
    # אין יותר לולאות, אין חישובי זמנים ואין שרשור מחרוזות ב-Main
    flights, routes = Manager.get_dashboard_data()

    return render_template('manager_dashboard.html', flights=flights, form_data={'routes': routes})

@app.route("/api/check_availability", methods=['POST'])
def check_availability_api():
    """API עבור ה-Wizard ליצירת טיסה"""
    if session.get("role") != "manager":
        return jsonify({"can_proceed": False, "error_msg": "Unauthorized"}), 403

    data = request.get_json()
    if not data or not data.get('route_id') or not data.get('dept_time'):
        return jsonify({"can_proceed": False, "error_msg": "Missing data"}), 400

    # הפעלת הלוגיקה דרך המודל
    response = Manager.validate_resources(data['dept_time'], data['route_id'])

    if not response:
        return jsonify({"can_proceed": False, "error_msg": "שגיאה בחישוב משאבים"}), 200

    return jsonify(response)


@app.route("/manager/cancel_flight", methods=["POST"])
def manager_cancel_flight_route():
    """ביטול טיסה ע"י מנהל"""
    if session.get("role") != "manager":
        flash("Unauthorized access.", "error")
        return redirect(url_for("manager_login_page"))

    flight_id = request.form.get("flight_id")
    if not flight_id:
        flash("Missing flight ID.", "error")
        return redirect(url_for("manager_dashboard"))

    # הפעלת הלוגיקה ב-Model (שקוראת ל-manager_cancel_flight_full_logic ב-DB)
    success, message = Manager.cancel_flight(flight_id)

    flash(message, "success" if success else "error")
    return redirect(url_for("manager_dashboard"))


@app.route("/manager/add_flight", methods=['POST'])
def add_flight():
    if session.get("role") != "manager":
        return redirect(url_for('manager_login_page'))

    manager_id = session.get('user_id')

    route_id = request.form.get('id_route')
    plane_id = request.form.get('id_plane')
    dept_time = request.form.get('departure_time')
    pilots = request.form.getlist('pilots')
    attendants = request.form.getlist('attendants')

    # --- השינוי: קליטת המחירים מהטופס ---
    price_economy = request.form.get('price_economy')
    price_business = request.form.get('price_business')  # יכול להיות ריק אם המטוס קטן

    # העברת המחירים למודל
    success, msg = Manager.create_flight(
        route_id, plane_id, dept_time, pilots, attendants, manager_id,
        price_economy, price_business
    )

    if success:
        flash("Flight created successfully!", "success")
    else:
        flash(f"Error creating flight: {msg}", "error")

    return redirect(url_for('manager_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home_page'))

if __name__ == '__main__':
    app.run(debug=True)
