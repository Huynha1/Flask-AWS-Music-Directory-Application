from flask import Flask, request, render_template, redirect, session
import boto3
from boto3.dynamodb.conditions import Key
# from boto3.resources.factory.dynamodb import Table

app = Flask(__name__, template_folder='template')
app.secret_key = '8x984iGllr'


# when hosting on ec2 change the above t othis
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
# or
# dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table('login')
music_table = dynamodb.Table('music')

# Login Page Route
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        response = table.query(
            KeyConditionExpression=Key('email').eq(email)
        )

        if response['Count'] == 1:
            item = response['Items'][0]
            if item['password'] == password:
                session['username'] = item['user_name']
                session['email'] = item['email']
                return redirect('/home')
            else:
                error = "email or password is invalid"
        else:
            error = "email or password is invalid"
    return render_template('login.html', error=error)

# Home Page Route
@app.route("/home", methods=["GET", "POST"])
def home():
    if 'username' in session:
        if request.method == "POST":
            return query()
        else:
            # Fetch user's subscriptions from the subscription table
            email = session['email']
            response = dynamodb.Table('subscription').query(
                KeyConditionExpression=Key('email').eq(email)
            )
            subscriptions = response['Items']
            s3 = boto3.client('s3')
            for item in subscriptions:
                artist = item['artist']
                try:
                    image_name = (artist + '.jpg').replace(' ', '')
                    image_url = s3.generate_presigned_url('get_object',
                                                          Params={'Bucket': 'artist-images-bucket', 'Key': image_name},
                                                          ExpiresIn=3600)
                    item['image_url'] = image_url
                except:
                    item['image_url'] = ''

            # Fetch all songs from the music table and add image URLs
            response = music_table.scan()
            items = response['Items']
            s3 = boto3.client('s3')
            for item in items:
                artist = item['artist']
                try:
                    image_name = (artist + '.jpg').replace(' ', '')
                    image_url = s3.generate_presigned_url('get_object',
                                                          Params={'Bucket': 'artist-images-bucket', 'Key': image_name},
                                                          ExpiresIn=3600)
                    item['image_url'] = image_url
                except:
                    item['image_url'] = ''

            exist_error = session.pop('exist_error', None)

            # Pass subscriptions and songs to template
            return render_template('home.html', username=session['username'], subscriptions=subscriptions, items=items, exist_error=exist_error)
    else:
        return redirect('/')


# Subscription Route
@app.route("/subscribe", methods=["POST"])
def subscribe():
    title = request.form['title']
    artist = request.form['artist']
    year = request.form['year']
    email = session['email']
    response = dynamodb.Table('subscription').query(
        KeyConditionExpression=Key('email').eq(email) & Key('title').eq(title)
    )
    if response['Count'] > 0:
        session['exist_error'] = "You are already subscribed to this item."
    else:
        dynamodb.Table('subscription').put_item(
            Item={
                'email': email,
                'title': title,
                'artist': artist,
                'year': year  
            }
        )
    return redirect('/home')

# Remove Route
@app.route("/remove", methods=["POST"])
def remove():
    email = request.form['email']
    title = request.form['title']
    dynamodb.Table('subscription').delete_item(
        Key={
            'email': email,
            'title': title
        }
    )
    return redirect('/home')

# Logout Route
@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect('/')

# Register Page Route
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        response = table.query(
            KeyConditionExpression=Key('email').eq(email)
        )
        if response['Count'] > 0:
            error = "The email already exists"
        else:
            table.put_item(
                Item={
                    'email': email,
                    'user_name': username,
                    'password': password
                }
            )
            return redirect('/')
    return render_template('register.html', error=error)

# Table Query Route
@app.route("/query", methods=["POST"])
def query():
    if 'username' in session:
        title = request.form.get('title')
        year = request.form.get('year')
        artist = request.form.get('artist')

        response = music_table.scan()
        items = response['Items']
        s3 = boto3.client('s3')
        filtered_items = []

        # add .lower() to ignore case sensitivity
        for item in items:
            if title and title.lower() != item.get('title').lower():
                continue
            if year and year != str(item.get('year')): # turn decimal value retrieved from the table string 
                continue
            if artist and artist.lower() != item.get('artist').lower():
                continue

            artist_name = item['artist']
            try:
                image_name = (artist_name + '.jpg').replace(' ', '')
                image_url = s3.generate_presigned_url('get_object',
                                                      Params={'Bucket': 'artist-images-bucket', 'Key': image_name},
                                                      ExpiresIn=3600)
                item['image_url'] = image_url
            except:
                item['image_url'] = ''
            filtered_items.append(item)

        if len(filtered_items) == 0:
            return render_template('home.html', username=session['username'], items=filtered_items, no_results=True)

        return render_template('home.html', username=session['username'], items=filtered_items)
    else:
        return redirect('/')

    
# Reset Query Route
@app.route("/reset", methods=["POST"])
def reset():
    session.pop('title', None)
    session.pop('year', None)
    session.pop('artist', None)
    return redirect('/home')

if __name__ == '__main__':
    app.run(debug=True)