from flask import Flask, render_template, request, session, redirect
# ייבוא הפונקציות מה-DB (כולל החדשה get_all_destinations)
from DB import (search_flights, user_login, email_exists, passport_exists, create_account, manager_login,
                chosen_flight_details, airplane_dimensions, get_all_destinations)
from utils import prepare_flights_for_view, build_seatmap_layout

app = Flask(__name__)
app.secret_key = "LironOfirNivi"


# ----------------
# home_page_screen
# ----------------
@app.route("/", methods=["GET"])
def home_page():
    # קבלת הנתונים מהטופס
    trip_type = (request.args.get("trip_type") or "oneway").strip()
    date = (request.args.get("date") or "").strip()
    return_date = (request.args.get("return_date") or "").strip()
    origin = (request.args.get("origin") or "").strip()
    destination = (request.args.get("destination") or "").strip()

    searched = bool(date or origin or destination)
    destinations = get_all_destinations()

    # מקרה 1: כניסה ראשונית
    if not searched:
        return render_template("home_page.html", date="", return_date="", origin="", destination="",
                               flights=None, error=None, destinations=destinations, trip_type=trip_type)

    # מקרה 2: חסרים פרטים
    if not (date and origin and destination):
        return render_template("home_page.html", date=date, return_date=return_date, origin=origin,
                               destination=destination, flights=None, error='Please fill all the fields.',
                               destinations=destinations, trip_type=trip_type)

    # מקרה 3: חיפוש
    flights = search_flights(date, origin, destination)

    if trip_type == "round" and return_date:
        return_flights = search_flights(return_date, destination, origin)
        flights.extend(return_flights)

    flights = prepare_flights_for_view(flights)

    return render_template("home_page.html",
                           date=date,
                           return_date=return_date,
                           origin=origin,
                           destination=destination,
                           flights=flights,
                           error=None,
                           destinations=destinations,
                           trip_type=trip_type)
# -----------------
# register_login
# -----------------

@app.route("/register-login", methods=["GET", "POST"])
def register_login_page():
    if request.method == "GET":
        return render_template("register_login.html", error=None)

    email = (request.form.get("email") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not email or not password:
        return render_template("register_login.html", error="Please enter email and password.")

    user = user_login(email, password)

    if user is None:
        return render_template("register_login.html", error="User not found. Please try again or continue as a guest",
                               email=email)

    session["email"] = user["email"]
    session["user_type"] = "registered"
    session["first_name"] = user["first_name_eng"]

    return redirect("/")


# -----------------
# register_logout
# -----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -----------
# create_account
# -----------

@app.route("/create-account", methods=["GET", "POST"])
def create_account_page():
    if request.method == "GET":
        return render_template("create_account.html", error=None)

    first_name_eng = (request.form.get("first_name") or "").strip()
    last_name_eng = (request.form.get("last_name") or "").strip()
    email = (request.form.get("email") or "").strip()
    birth_date = (request.form.get("date_of_birth") or "").strip()
    passport = (request.form.get("passport_number") or "").strip()
    password = (request.form.get("password") or "").strip()

    phone_numbers = request.form.getlist("phone_numbers")
    phone_numbers = [phone.strip() for phone in phone_numbers if phone and phone.strip()]

    if not all([first_name_eng, last_name_eng, email, birth_date, passport, password]) or not phone_numbers:
        return render_template(
            "create_account.html",
            error="Please fill all the fields.",
            first_name=first_name_eng, last_name=last_name_eng, email=email,
            date_of_birth=birth_date, passport_number=passport, )

    if email_exists(email):
        return render_template("create_account.html", error="This email is already registered.",
                               first_name=first_name_eng, last_name=last_name_eng, email=email,
                               date_of_birth=birth_date,
                               passport_number=passport)

    if passport_exists(passport):
        return render_template("create_account.html", error="This passport number is already registered.",
                               first_name=first_name_eng, last_name=last_name_eng, email=email,
                               date_of_birth=birth_date, passport_number=passport)

    create_account(email, first_name_eng, last_name_eng, birth_date, passport, password, phone_numbers)

    session["user_type"] = "registered"
    session["email"] = email
    session["first_name"] = first_name_eng

    return redirect("/")


# -----------------
# manager_login
# -----------------

@app.route("/manager-login", methods=["GET", "POST"])
def manager_login_page():
    if request.method == "GET":
        return render_template("manager_login.html", error=None, id_worker="")

    id_worker = (request.form.get("id_worker") or "").strip()
    password = (request.form.get("password") or "").strip()

    if not id_worker or not password:
        return render_template("manager_login.html", error="Please enter ID and password.", id_worker=id_worker)

    manager = manager_login(id_worker, password)

    if manager is None:
        return render_template("manager_login.html", error="Manager not found. Please try again",
                               id_worker=id_worker)

    session["id_worker"] = manager["id_worker"]
    session["user_type"] = "manager"
    session["first_name"] = manager["first_name"]

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, render_template, request, session, redirect, url_for, flash
import mysql.connector
from datetime import datetime, timedelta

# --- ייבוא פונקציית החיבור מהקובץ החיצוני שלך ---
from DB import get_connection

app = Flask(__name__)
app.secret_key = 'LironOfirNivi'

@app.route('/')
def home():
    return redirect(url_for('view_bookings'))

@app.route('/my-bookings', methods=['GET', 'POST'])
def view_bookings():
    email = session.get('email')
    
    # אם המשתמש לא מחובר אבל שלח אימייל בטופס (למשל אורח)
    id_booking = None
    if not email and request.method == 'POST':
        email = request.form.get('email')
        id_booking = request.form.get('id_booking')

    if email:
        # שימוש בפונקציה החדשה שיצרנו ב-DB
        bookings_dict = get_user_bookings(email, id_booking)
        
        current_time = datetime.now()
        future = []
        past = []

        for b in bookings_dict.values():
            flight_time = b['info']['departure_time']
            if isinstance(flight_time, str):
                flight_time = datetime.strptime(flight_time, '%Y-%m-%d %H:%M:%S')

            if flight_time >= current_time:
                future.append(b)
            else:
                past.append(b)

        return render_template('bookings_results.html', future=future, past=past, email=email)

    return render_template('search_bookings.html')

# -----------------
# Cancel Booking (New)
# -----------------
@app.route('/cancel-booking', methods=['POST'])
def cancel_booking():
    booking_id = request.form.get('booking_id')
    
    # שימוש בפונקציה החדשה ב-DB
    success, message = cancel_booking_in_db(booking_id)
    
    flash(message)
    return redirect(url_for('view_bookings'))

if __name__ == "__main__":
    app.run(debug=True) # תריץ רק אפליקציה אחת


#-----------------
#select_seats
#-----------------
@app.route("/select-seats", methods=["GET"])
def select_seats_page():

    flight_id = request.args.get("flight_id", type=int)
    if not flight_id:
        return redirect("/")

    flight = chosen_flight_details(flight_id)
    if not flight:
        return redirect("/")

    flight = prepare_flights_for_view([flight])[0]

    plane = plane_object(flight_id)
    if plane is None:
        return redirect("/")

    occupied_tickets = get_occupied_seats(flight_id)
    occupied_map = occupied_seats(occupied_tickets)

    col_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    seats_prices = get_flight_prices(flight_id)

    formatted_prices = {k: format_price(v) for k, v in seats_prices.items()}

    return render_template("select_seats.html", plane=plane,occupied=occupied_map, flight=flight,
                           col_letters=col_letters, prices=formatted_prices)


#-----------------
#process_booking
#-----------------
@app.route("/process-booking", methods=["POST"])
def process_booking():
    # 1. קבלת הנתונים מהטופס
    flight_id = request.form.get("flight_id", type=int)
    selected_seats = request.form.getlist("seats")  # רשימה: ['Business-1-A', ...]

    if not selected_seats:
        flash("Please select at least one seat.")
        return redirect(url_for('select_seats_page', flight_id=flight_id))

    # 2. שליפת המצב העדכני ביותר מהדאטה-בייס (שאילתה חדשה)
    # זו הפונקציה שכבר קיימת לך ב-DB.py
    latest_occupied_data = get_occupied_seats(flight_id)

    # 3. בדיקת זמינות באמצעות הפונקציה ב-utils
    conflicts = validate_seat_selection(selected_seats, latest_occupied_data)

    # 4. טיפול בתוצאה
    if conflicts:
        # אם יש התנגשויות - מחזירים אחורה עם שגיאה
        conflict_msg = ", ".join(conflicts)
        flash(f"Oops! The following seats were just taken: {conflict_msg}. Please choose different seats.")
        return redirect(url_for('select_seats_page', flight_id=flight_id))

    else:
        # הכל פנוי!
        # שומרים ב-Session בלבד (עדיין לא בדאטה בייס)
        session['current_booking'] = {
            'flight_id': flight_id,
            'seats': selected_seats}
        # מעבירים לעמוד הבא (פרטי כרטיסים/תשלום)
        return redirect(url_for('tickets_details_page'))

