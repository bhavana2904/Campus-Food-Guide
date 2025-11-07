from flask import Flask, render_template, request, redirect, session, flash, send_from_directory, jsonify
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets
from werkzeug.utils import secure_filename
import logging
import json

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET') or secrets.token_hex(32)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.logger.setLevel(logging.DEBUG)

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='btsbutter123',  # Remember to change this!
        db='food',
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/templates/public/<path:filename>')
def serve_templates_public(filename):
    return send_from_directory(os.path.join(app.root_path, 'templates', 'public'), filename)

@app.route('/')
def index():
    return render_template('index.html', 
                         logged_in=('user_id' in session), 
                         username=session.get('username'), 
                         profile_image_url=session.get('profile_image_url'), 
                         user_id=session.get('user_id'), 
                         email=session.get('email'), 
                         show_profile=False)

@app.route('/register', methods=['POST'])
def register():
    full_name = request.form['full_name']
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    student_id = request.form.get('student_id')
    uploaded_file = request.files.get('profile_pic')

    hashed_password = generate_password_hash(password)
    profile_image_url = None

    if uploaded_file and allowed_file(uploaded_file.filename):
        filename = secure_filename(uploaded_file.filename)
        unique_name = f"{secrets.token_hex(8)}_{filename}"
        uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
        profile_image_url = f"/static/uploads/{unique_name}"

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
            if cursor.fetchone():
                flash("Email or username already exists!")
                return redirect('/')
            
            cursor.execute("""
                INSERT INTO users (full_name, username, email, password, student_id, profile_image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (full_name, username, email, hashed_password, student_id, profile_image_url))
            conn.commit()
    finally:
        conn.close()
    
    flash("Registration successful!")
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    identifier = request.form['identifier']
    password = request.form['password']

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s OR username = %s", (identifier, identifier))
            user = cursor.fetchone()
    finally:
        conn.close()

    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['email'] = user.get('email')
        session['profile_image_url'] = user.get('profile_image_url')
        flash("Login successful!")
        return redirect('/profile')
    else:
        flash("Invalid credentials!")
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect('/')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('index.html', 
                         logged_in=True, 
                         username=session.get('username'), 
                         profile_image_url=session.get('profile_image_url'), 
                         user_id=session.get('user_id'), 
                         email=session.get('email'), 
                         show_profile=True)

@app.route('/canteen/<int:canteen_id>')
def view_canteen(canteen_id):
    """Render the main page with instructions to open a specific canteen view."""
    conn = get_db_connection()
    canteen_name = ''
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM canteens WHERE canteen_id = %s", (canteen_id,))
            canteen = cursor.fetchone()
            if canteen:
                canteen_name = canteen.get('name', '')
    finally:
        conn.close()

    return render_template('index.html', 
                         logged_in=('user_id' in session), 
                         username=session.get('username'), 
                         profile_image_url=session.get('profile_image_url'), 
                         user_id=session.get('user_id'), 
                         email=session.get('email'), 
                         show_profile=False, 
                         show_canteen=True, 
                         canteen_id=canteen_id,
                         canteen_name=canteen_name)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        flash('Please sign in to submit a review.')
        return redirect('/')

    food_name = request.form.get('food_name')
    price = request.form.get('price')
    rating = request.form.get('rating')
    spice_level = request.form.get('spice_level')
    review_text = request.form.get('review')
    canteen_id = request.form.get('canteen_id')

    app.logger.debug('submit_review - canteen_id: %s', canteen_id)

    if not food_name or food_name.strip() == '':
        flash('Food name is required.')
        return redirect(request.referrer or '/')

    if not canteen_id or canteen_id == 'null' or canteen_id == '':
        flash('Please select a canteen.')
        return redirect('/')

    try:
        price_val = float(price) if price not in (None, '') else 0.0
    except Exception:
        flash('Price must be a number.')
        return redirect(request.referrer or '/')

    try:
        rating_val = int(rating) if rating not in (None, '') else 0
    except Exception:
        rating_val = 0

    try:
        spice_val = int(spice_level) if spice_level not in (None, '') else 0
    except Exception:
        spice_val = 0

    images = request.files.getlist('images')
    image_paths = []
    if images:
        for f in images:
            if f and f.filename and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                unique_name = f"{secrets.token_hex(8)}_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                f.save(save_path)
                image_paths.append(f"/static/uploads/{unique_name}")

    if not image_paths:
        image_paths = ['https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&h=200&fit=crop']

    image_paths_json = json.dumps(image_paths)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO FoodReviews (FoodName, Price, Rating, SpiceLevel, Review, ImagePaths, UserID, CanteenID)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (food_name, price_val, rating_val, spice_val, review_text, image_paths_json, session.get('user_id'), canteen_id))
            # get inserted review id and also insert a UserActivity row
            review_id = cursor.lastrowid
            try:
                cursor.execute("INSERT INTO UserActivity (UserID, PostID, ActivityType) VALUES (%s, %s, %s)", (session.get('user_id'), review_id, 'review'))
            except Exception:
                # If UserActivity table doesn't exist or insert fails, log and continue
                app.logger.exception('Failed to insert UserActivity for new review')
            conn.commit()
            app.logger.debug('Review inserted successfully!')
    except Exception as e:
        app.logger.exception('Error inserting FoodReviews row')
        flash(f"Error saving review: {e}")
        return redirect(request.referrer or '/')
    finally:
        conn.close()

    flash('Review submitted successfully!')
    
    try:
        canteen_id_int = int(canteen_id)
        return redirect(f"/canteen/{canteen_id_int}")
    except Exception as e:
        app.logger.error(f'Error redirecting to canteen page: {e}')
        return redirect('/')

# API ENDPOINTS
@app.route('/api/canteens')
def api_canteens():
    """Return list of canteens as JSON."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT canteen_id, name, description, image_url, location FROM canteens ORDER BY name")
            rows = cursor.fetchall()
            canteens = []
            for r in rows:
                canteens.append({
                    'id': r.get('canteen_id'),
                    'name': r.get('name'),
                    'description': r.get('description') or '',
                    'image_url': r.get('image_url') or '',
                    'location': r.get('location') or ''
                })
    finally:
        conn.close()

    return jsonify({ 'success': True, 'canteens': canteens })

@app.route('/api/canteen_reviews')
def api_canteen_reviews():
    """API endpoint to fetch reviews for a specific canteen as JSON."""
    canteen_id = request.args.get('canteen_id')
    if not canteen_id:
        return jsonify({ 'success': False, 'error': 'canteen_id required' }), 400

    try:
        canteen_id_int = int(canteen_id)
    except Exception:
        return jsonify({ 'success': False, 'error': 'invalid canteen_id' }), 400

    # allow frontend to request different sort modes via ?sort=<key>
    # supported keys: upvotes, popular, spice_desc, spice_asc, newest, price_asc, price_desc
    sort_key = request.args.get('sort', '').lower()

    # Use the SELECT aliases (Price, Rating, SpiceLevel, SubmissionDate) in ORDER BY
    # to avoid ONLY_FULL_GROUP_BY related errors when grouping.
    order_clause = 'SubmissionDate DESC'
    if sort_key == 'upvotes':
        order_clause = 'upvotes DESC'
    elif sort_key == 'popular':
        # popularity: first by upvotes then by rating
        order_clause = 'upvotes DESC, Rating DESC'
    elif sort_key == 'spice_desc':
        order_clause = 'SpiceLevel DESC'
    elif sort_key == 'spice_asc':
        order_clause = 'SpiceLevel ASC'
    elif sort_key in ('price_asc', 'price'):
        # accept both price_asc and price from frontend
        order_clause = 'Price ASC'
    elif sort_key == 'price_desc':
        order_clause = 'Price DESC'
    elif sort_key == 'newest':
        order_clause = 'SubmissionDate DESC'

    conn = get_db_connection()
    results = []
    try:
        with conn.cursor() as cursor:
            try:
                # compute upvotes in the same query to avoid N+1 COUNT queries
                # Use ANY_VALUE for non-aggregated columns to be safe with ONLY_FULL_GROUP_BY
                sql = f"""
                    SELECT
                        r.ReviewID,
                        ANY_VALUE(r.FoodName) AS FoodName,
                        ANY_VALUE(r.Price) AS Price,
                        ANY_VALUE(r.Rating) AS Rating,
                        ANY_VALUE(r.SpiceLevel) AS SpiceLevel,
                        ANY_VALUE(r.Review) AS Review,
                        ANY_VALUE(r.ImagePaths) AS ImagePaths,
                        ANY_VALUE(r.UserID) AS UserID,
                        ANY_VALUE(r.CanteenID) AS CanteenID,
                        ANY_VALUE(r.SubmissionDate) AS SubmissionDate,
                        ANY_VALUE(u.username) AS username,
                        COUNT(up.UpvoteID) AS upvotes
                    FROM FoodReviews r
                    LEFT JOIN users u ON r.UserID = u.user_id
                    LEFT JOIN Upvotes up ON r.ReviewID = up.ReviewID
                    WHERE r.CanteenID = %s
                    GROUP BY r.ReviewID
                    ORDER BY {order_clause}
                """
                cursor.execute(sql, (canteen_id_int,))
            except pymysql.err.ProgrammingError as e:
                if e.args and e.args[0] == 1146:
                    app.logger.warning('FoodReviews or related table missing')
                    return jsonify({ 'success': True, 'reviews': [] })
                raise

            rows = cursor.fetchall()
            app.logger.debug(f"Found {len(rows)} reviews for canteen {canteen_id_int} (sort={sort_key})")

            for r in rows:
                images = []
                try:
                    if r.get('ImagePaths'):
                        parsed = json.loads(r['ImagePaths']) if isinstance(r['ImagePaths'], str) else r['ImagePaths']
                        images = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    if r.get('ImagePaths'):
                        images = [p.strip() for p in (r['ImagePaths'] or '').split(',') if p.strip()]

                if not images:
                    images = ['https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&h=200&fit=crop']

                upvotes_count = int(r.get('upvotes') or 0)

                # load comments for this review (could be optimized to single query if needed)
                comments_list = []
                try:
                    cursor.execute("SELECT c.CommentID, c.CommentText, c.CommentDate, u.username, c.UserID AS comment_user_id FROM Comments c LEFT JOIN users u ON c.UserID = u.user_id WHERE c.ReviewID = %s ORDER BY c.CommentDate ASC", (r['ReviewID'],))
                    cm_rows = cursor.fetchall()
                    for cr in cm_rows:
                        comments_list.append({
                            'id': cr.get('CommentID'),
                            'author': cr.get('username'),
                            'user_id': cr.get('comment_user_id'),
                            'text': cr.get('CommentText'),
                            'date': str(cr.get('CommentDate'))
                        })
                except pymysql.err.ProgrammingError as e:
                    if not (e.args and e.args[0] == 1146):
                        raise

                results.append({
                    'id': r['ReviewID'],
                    'canteen_id': r.get('CanteenID'),
                    'images': images,
                    'image': images[0],
                    'name': r.get('FoodName'),
                    'rating': int(r.get('Rating') or 0),
                    'price': float(r.get('Price') or 0.0),
                    'spiceLevel': int(r.get('SpiceLevel') or 0),
                    'author': r.get('username') or 'Unknown',
                    'author_id': r.get('UserID'),
                    'upvotes': upvotes_count,
                    'review': r.get('Review') or '',
                    'comments': comments_list
                })
    except Exception as e:
        app.logger.exception('Error in api_canteen_reviews')
        return jsonify({ 'success': False, 'error': str(e) }), 500
    finally:
        conn.close()

    return jsonify({ 'success': True, 'reviews': results })


@app.route('/api/my_reviews')
def api_my_reviews():
    """Return reviews created by the currently logged-in user."""
    if 'user_id' not in session:
        return jsonify({ 'success': False, 'error': 'not_logged_in' }), 401

    user_id = session['user_id']
    conn = get_db_connection()
    results = []
    try:
        with conn.cursor() as cursor:
            try:
                cursor.execute("""
                    SELECT r.*, u.username FROM FoodReviews r
                    LEFT JOIN users u ON r.UserID = u.user_id
                    WHERE r.UserID = %s
                    ORDER BY r.SubmissionDate DESC
                """, (user_id,))
            except pymysql.err.ProgrammingError as e:
                # Table might not exist yet
                if e.args and e.args[0] == 1146:
                    app.logger.warning('FoodReviews table missing')
                    return jsonify({ 'success': True, 'reviews': [] })
                raise

            rows = cursor.fetchall()
            for r in rows:
                images = []
                try:
                    if r.get('ImagePaths'):
                        parsed = json.loads(r['ImagePaths']) if isinstance(r['ImagePaths'], str) else r['ImagePaths']
                        images = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    if r.get('ImagePaths'):
                        images = [p.strip() for p in (r['ImagePaths'] or '').split(',') if p.strip()]

                if not images:
                    images = ['https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&h=200&fit=crop']

                upvotes_count = 0
                try:
                    cursor.execute("SELECT COUNT(*) AS cnt FROM Upvotes WHERE ReviewID = %s", (r['ReviewID'],))
                    cnt_row = cursor.fetchone()
                    upvotes_count = cnt_row['cnt'] if cnt_row and 'cnt' in cnt_row else 0
                except pymysql.err.ProgrammingError as e:
                    if not (e.args and e.args[0] == 1146):
                        raise

                # load comments for this review
                comments_list = []
                try:
                    cursor.execute("SELECT c.CommentID, c.CommentText, c.CommentDate, u.username, c.UserID AS comment_user_id FROM Comments c LEFT JOIN users u ON c.UserID = u.user_id WHERE c.ReviewID = %s ORDER BY c.CommentDate ASC", (r['ReviewID'],))
                    cm_rows = cursor.fetchall()
                    for cr in cm_rows:
                        comments_list.append({
                            'id': cr.get('CommentID'),
                            'author': cr.get('username'),
                            'user_id': cr.get('comment_user_id'),
                            'text': cr.get('CommentText'),
                            'date': str(cr.get('CommentDate'))
                        })
                except pymysql.err.ProgrammingError as e:
                    if not (e.args and e.args[0] == 1146):
                        raise

                results.append({
                    'id': r['ReviewID'],
                    'canteen_id': r.get('CanteenID'),
                    'images': images,
                    'image': images[0],
                    'name': r.get('FoodName'),
                    'rating': int(r.get('Rating') or 0),
                    'price': float(r.get('Price') or 0.0),
                    'spiceLevel': int(r.get('SpiceLevel') or 0),
                    'author': r.get('username') or 'Unknown',
                    'author_id': r.get('UserID'),
                    'upvotes': upvotes_count,
                    'review': r.get('Review') or '',
                    'comments': comments_list
                })
    except Exception as e:
        app.logger.exception('Error in api_my_reviews')
        return jsonify({ 'success': False, 'error': str(e) }), 500
    finally:
        conn.close()

    return jsonify({ 'success': True, 'reviews': results })


@app.route('/api/reviews_by_ids')
def api_reviews_by_ids():
    """Return multiple reviews by a comma-separated list of ids provided in `ids` query param."""
    ids_raw = request.args.get('ids')
    if not ids_raw:
        return jsonify({ 'success': False, 'error': 'ids parameter required' }), 400

    try:
        ids = [int(x) for x in ids_raw.split(',') if x.strip()]
    except Exception:
        return jsonify({ 'success': False, 'error': 'invalid ids parameter' }), 400

    if not ids:
        return jsonify({ 'success': True, 'reviews': [] })

    conn = get_db_connection()
    results = []
    try:
        with conn.cursor() as cursor:
            try:
                sql = f"SELECT r.*, u.username FROM FoodReviews r LEFT JOIN users u ON r.UserID = u.user_id WHERE r.ReviewID IN ({', '.join(['%s']*len(ids))}) ORDER BY FIELD(r.ReviewID, {', '.join(['%s']*len(ids))})"
                params = ids + ids
                cursor.execute(sql, params)
            except pymysql.err.ProgrammingError as e:
                if e.args and e.args[0] == 1146:
                    app.logger.warning('FoodReviews table missing')
                    return jsonify({ 'success': True, 'reviews': [] })
                raise

            rows = cursor.fetchall()
            for r in rows:
                images = []
                try:
                    if r.get('ImagePaths'):
                        parsed = json.loads(r['ImagePaths']) if isinstance(r['ImagePaths'], str) else r['ImagePaths']
                        images = parsed if isinstance(parsed, list) else [parsed]
                except Exception:
                    if r.get('ImagePaths'):
                        images = [p.strip() for p in (r['ImagePaths'] or '').split(',') if p.strip()]

                if not images:
                    images = ['https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&h=200&fit=crop']

                upvotes_count = 0
                try:
                    cursor.execute("SELECT COUNT(*) AS cnt FROM Upvotes WHERE ReviewID = %s", (r['ReviewID'],))
                    cnt_row = cursor.fetchone()
                    upvotes_count = cnt_row['cnt'] if cnt_row and 'cnt' in cnt_row else 0
                except pymysql.err.ProgrammingError as e:
                    if not (e.args and e.args[0] == 1146):
                        raise

                # load comments for this review
                comments_list = []
                try:
                    cursor.execute("SELECT c.CommentID, c.CommentText, c.CommentDate, u.username, c.UserID AS comment_user_id FROM Comments c LEFT JOIN users u ON c.UserID = u.user_id WHERE c.ReviewID = %s ORDER BY c.CommentDate ASC", (r['ReviewID'],))
                    cm_rows = cursor.fetchall()
                    for cr in cm_rows:
                        comments_list.append({
                            'id': cr.get('CommentID'),
                            'author': cr.get('username'),
                            'user_id': cr.get('comment_user_id'),
                            'text': cr.get('CommentText'),
                            'date': str(cr.get('CommentDate'))
                        })
                except pymysql.err.ProgrammingError as e:
                    if not (e.args and e.args[0] == 1146):
                        raise

                results.append({
                    'id': r['ReviewID'],
                    'canteen_id': r.get('CanteenID'),
                    'images': images,
                    'image': images[0],
                    'name': r.get('FoodName'),
                    'rating': int(r.get('Rating') or 0),
                    'price': float(r.get('Price') or 0.0),
                    'spiceLevel': int(r.get('SpiceLevel') or 0),
                    'author': r.get('username') or 'Unknown',
                    'author_id': r.get('UserID'),
                    'upvotes': upvotes_count,
                    'review': r.get('Review') or '',
                    'comments': comments_list
                })
    except Exception as e:
        app.logger.exception('Error in api_reviews_by_ids')
        return jsonify({ 'success': False, 'error': str(e) }), 500
    finally:
        conn.close()

    return jsonify({ 'success': True, 'reviews': results })

@app.route('/api/me')
def api_me():
    if 'user_id' not in session:
        return jsonify({ 'logged_in': False })

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username, profile_image_url FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone() or {}
            
            favs = []
            ups = []
            try:
                cursor.execute("SELECT ReviewID FROM Favorites WHERE UserID = %s", (user_id,))
                favs = [r['ReviewID'] for r in cursor.fetchall()]
            except pymysql.err.ProgrammingError as e:
                if e.args and e.args[0] != 1146:
                    raise

            try:
                cursor.execute("SELECT ReviewID FROM Upvotes WHERE UserID = %s", (user_id,))
                ups = [r['ReviewID'] for r in cursor.fetchall()]
            except pymysql.err.ProgrammingError as e:
                if e.args and e.args[0] != 1146:
                    raise
    finally:
        conn.close()

    return jsonify({
        'logged_in': True,
        'user_id': user_id,
        'username': user.get('username'),
        'profile_image_url': user.get('profile_image_url'),
        'favorites': favs,
        'upvoted': ups
    })

@app.route('/upvote/<int:review_id>', methods=['POST'])
def upvote_review(review_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            try:
                cursor.execute("SELECT * FROM Upvotes WHERE UserID = %s AND ReviewID = %s", (user_id, review_id))
            except pymysql.err.ProgrammingError as e:
                if e.args and e.args[0] == 1146:
                    return jsonify({ 'success': False, 'error': 'Upvotes table does not exist' }), 500
                raise
            exists = cursor.fetchone() is not None
            if exists:
                cursor.execute("DELETE FROM Upvotes WHERE UserID = %s AND ReviewID = %s", (user_id, review_id))
                # remove corresponding activity rows (best-effort)
                try:
                    cursor.execute("DELETE FROM UserActivity WHERE UserID = %s AND PostID = %s AND ActivityType = %s", (user_id, review_id, 'upvote'))
                except Exception:
                    app.logger.exception('Failed to delete UserActivity for upvote')
                upvoted = False
            else:
                try:
                    cursor.execute("INSERT INTO Upvotes (UserID, ReviewID) VALUES (%s, %s)", (user_id, review_id))
                except pymysql.err.OperationalError as e:
                    # MySQL SIGNAL uses SQLSTATE '45000' and returns errno 1644 in PyMySQL
                    msg = str(e)
                    app.logger.debug('Upvote insert failed: %s', msg)
                    if (hasattr(e, 'args') and len(e.args) > 0 and e.args[0] == 1644) or 'Cannot upvote' in msg:
                        # Friendly response for UI
                        conn.close()
                        return jsonify({ 'success': False, 'error': 'You cannot upvote your own review' }), 400
                    raise

                # add activity row
                try:
                    cursor.execute("INSERT INTO UserActivity (UserID, PostID, ActivityType) VALUES (%s, %s, %s)", (user_id, review_id, 'upvote'))
                except Exception:
                    app.logger.exception('Failed to insert UserActivity for upvote')
                upvoted = True

            cursor.execute("SELECT COUNT(*) AS cnt FROM Upvotes WHERE ReviewID = %s", (review_id,))
            upvotes_count = cursor.fetchone()['cnt']
        conn.commit()
    finally:
        conn.close()

    return jsonify({
        'success': True,
        'upvoted': upvoted,
        'upvotes': upvotes_count
    })

@app.route('/favorite/<int:review_id>', methods=['POST'])
def favorite_review(review_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            try:
                cursor.execute("SELECT * FROM Favorites WHERE UserID = %s AND ReviewID = %s", (user_id, review_id))
            except pymysql.err.ProgrammingError as e:
                if e.args and e.args[0] == 1146:
                    return jsonify({ 'success': False, 'error': 'Favorites table does not exist' }), 500
                raise
            exists = cursor.fetchone() is not None
            if exists:
                cursor.execute("DELETE FROM Favorites WHERE UserID = %s AND ReviewID = %s", (user_id, review_id))
                try:
                    cursor.execute("DELETE FROM UserActivity WHERE UserID = %s AND PostID = %s AND ActivityType = %s", (user_id, review_id, 'favorite'))
                except Exception:
                    app.logger.exception('Failed to delete UserActivity for favorite')
                favorited = False
            else:
                try:
                    cursor.execute("INSERT INTO Favorites (UserID, ReviewID) VALUES (%s, %s)", (user_id, review_id))
                except pymysql.err.OperationalError as e:
                    msg = str(e)
                    app.logger.debug('Favorite insert failed: %s', msg)
                    if (hasattr(e, 'args') and len(e.args) > 0 and e.args[0] == 1644) or 'Cannot favorite' in msg:
                        conn.close()
                        return jsonify({ 'success': False, 'error': 'You cannot favorite your own review' }), 400
                    raise

                try:
                    cursor.execute("INSERT INTO UserActivity (UserID, PostID, ActivityType) VALUES (%s, %s, %s)", (user_id, review_id, 'favorite'))
                except Exception:
                    app.logger.exception('Failed to insert UserActivity for favorite')
                favorited = True

            cursor.execute("SELECT COUNT(*) AS cnt FROM Favorites WHERE ReviewID = %s", (review_id,))
            favorites_count = cursor.fetchone()['cnt']
        conn.commit()
    finally:
        conn.close()

    return jsonify({
        'success': True,
        'favorited': favorited,
        'favorites': favorites_count
    })

@app.route('/comment/<int:review_id>', methods=['POST'])
def post_comment(review_id):
    if 'user_id' not in session:
        return jsonify({ 'success': False, 'error': 'Unauthorized' }), 401

    comment_text = request.form.get('comment')
    if not comment_text or comment_text.strip() == '':
        return jsonify({ 'success': False, 'error': 'Comment cannot be empty' }), 400

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO Comments (ReviewID, UserID, CommentText)
                VALUES (%s, %s, %s)
            """, (review_id, user_id, comment_text))
            comment_id = cursor.lastrowid
            try:
                cursor.execute("INSERT INTO UserActivity (UserID, PostID, ActivityType) VALUES (%s, %s, %s)", (user_id, review_id, 'comment'))
            except Exception:
                app.logger.exception('Failed to insert UserActivity for comment')
        conn.commit()
    finally:
        conn.close()

    return jsonify({ 'success': True, 'message': 'Comment posted successfully' })


@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return jsonify({ 'success': False, 'error': 'Unauthorized' }), 401

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Ensure the comment exists and belongs to the current user
            cursor.execute("SELECT ReviewID FROM Comments WHERE CommentID = %s AND UserID = %s", (comment_id, user_id))
            row = cursor.fetchone()
            if not row:
                return jsonify({ 'success': False, 'error': 'not_found_or_not_owner' }), 404

            review_id = row.get('ReviewID')

            # Delete the comment (owner verified above)
            cursor.execute("DELETE FROM Comments WHERE CommentID = %s AND UserID = %s", (comment_id, user_id))

            # Best-effort: remove corresponding UserActivity rows for this comment
            try:
                cursor.execute("DELETE FROM UserActivity WHERE UserID = %s AND PostID = %s AND ActivityType = %s", (user_id, review_id, 'comment'))
            except Exception:
                app.logger.exception('Failed to delete UserActivity for comment')

        conn.commit()
    finally:
        conn.close()

    return jsonify({ 'success': True, 'message': 'Comment deleted' })


@app.route('/review/<int:review_id>/delete', methods=['POST'])
def delete_review(review_id):
    """Delete a FoodReviews row owned by the current user.

    This endpoint:
    - verifies the requester owns the review (or can be extended for admins)
    - deletes dependent rows (Upvotes, Favorites, UserActivity) to avoid FK errors
    - deletes the FoodReviews row
    - removes any locally stored image files referenced in ImagePaths
    """
    if 'user_id' not in session:
        return jsonify({ 'success': False, 'error': 'Unauthorized' }), 401

    user_id = session['user_id']
    conn = get_db_connection()
    image_paths = None
    try:
        with conn.cursor() as cursor:
            # fetch owner and image paths
            cursor.execute("SELECT UserID, ImagePaths FROM FoodReviews WHERE ReviewID = %s", (review_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({ 'success': False, 'error': 'not_found' }), 404

            owner_id = row.get('UserID')
            image_paths = row.get('ImagePaths')

            # Ownership check (extend here to allow admins)
            if owner_id != user_id:
                return jsonify({ 'success': False, 'error': 'not_owner' }), 403

            # Delete dependent records first to avoid FK constraint issues
            try:
                cursor.execute("DELETE FROM Upvotes WHERE ReviewID = %s", (review_id,))
            except Exception:
                app.logger.exception('Failed to delete Upvotes for review %s', review_id)

            try:
                cursor.execute("DELETE FROM Favorites WHERE ReviewID = %s", (review_id,))
            except Exception:
                app.logger.exception('Failed to delete Favorites for review %s', review_id)

            try:
                cursor.execute("DELETE FROM UserActivity WHERE PostID = %s", (review_id,))
            except Exception:
                app.logger.exception('Failed to delete UserActivity for review %s', review_id)

            # Comments may have ON DELETE CASCADE; delete explicitly if you prefer
            try:
                cursor.execute("DELETE FROM Comments WHERE ReviewID = %s", (review_id,))
            except Exception:
                app.logger.exception('Failed to delete Comments for review %s', review_id)

            # Finally delete the review row
            cursor.execute("DELETE FROM FoodReviews WHERE ReviewID = %s AND UserID = %s", (review_id, user_id))

        conn.commit()
    finally:
        conn.close()

    # Remove local image files referenced in ImagePaths (best-effort)
    try:
        if image_paths:
            # ImagePaths stored as JSON array or comma-separated string
            imgs = []
            try:
                imgs = json.loads(image_paths) if isinstance(image_paths, str) else image_paths
                if not isinstance(imgs, list):
                    imgs = [imgs]
            except Exception:
                # Fallback: comma-separated
                imgs = [p.strip() for p in (image_paths or '').split(',') if p.strip()]

            for p in imgs:
                # Only delete local uploads (avoid removing external URLs)
                if isinstance(p, str) and p.startswith('/static/uploads/'):
                    local_path = os.path.join(app.root_path, p.lstrip('/'))
                    try:
                        if os.path.exists(local_path):
                            os.remove(local_path)
                            app.logger.debug('Deleted image file %s', local_path)
                    except Exception:
                        app.logger.exception('Failed to remove image file %s', local_path)
    except Exception:
        app.logger.exception('Error while cleaning up image files for review %s', review_id)

    return jsonify({ 'success': True, 'message': 'Review deleted' })
@app.route('/api/activity_feed')
def api_activity_feed():
    if 'user_id' not in session:
        return jsonify({ 'success': False, 'error': 'Unauthorized' }), 401

    user_id = session['user_id']
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT a.ActivityType, a.ActivityTime, r.FoodName, r.ReviewID
                FROM UserActivity a
                LEFT JOIN FoodReviews r ON a.PostID = r.ReviewID
                WHERE a.UserID = %s
                ORDER BY a.ActivityTime DESC
                LIMIT 50
            """, (user_id,))
            feed = cursor.fetchall()
    finally:
        conn.close()

    return jsonify({ 'success': True, 'activity': feed })


if __name__ == '__main__':
    app.run(debug=True)

