#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, abort, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from models import db, Artist, Venue, Show
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from datetime import datetime, timezone
from flask_wtf import Form
from sqlalchemy import or_, desc
from forms import *
import sys
import collections
from flask_wtf.csrf import CsrfProtect
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
CsrfProtect(app)
db.init_app(app)


# TODO: connect to a local postgresql database
#Linking my DB with migration
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#
collections.Callable = collections.abc.Callable

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

# Error Message
def show_form_errors(fieldName, errorMessages):
    return flash(
        'Some errors on ' +
        fieldName.replace('_', ' ') +
        ': ' +
        ' '.join([str(message) for message in errorMessages]),
        'warning'
    )

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  #querying Venue table to get all Cities
  cities = db.session.query(Venue.city).group_by(Venue.city).all()
  current_time = datetime.now(timezone.utc)
  current_city=' '
  #initializing empty data array
  data=[]
  for city in cities:
      venues = db.session.query(Venue).filter(Venue.city == city[0]).order_by('id').all()
      for venue in venues:
          num_upcoming_shows = venue.shows.filter(Show.show_start_time > current_time).all()       
          if current_city != venue.city:
                #adding data to our data array if it does not already exist
                data.append({
                "city":venue.city,
                "state":venue.state,
                "venues":[{
                "id": venue.id,
                "name":venue.name,
                "num_upcoming_shows": len(num_upcoming_shows)}]
                })
                current_city=venue.city
          else: 
            data[len(data) - 1]["venues"].append({
                "id": venue.id,
                "name":venue.name,
                "num_upcoming_shows": len(num_upcoming_shows)
              })
  return render_template('pages/venues.html', areas=data)

#Venue Search
@app.route('/venues/search', methods=['POST'])
def search_venues():
  term = request.form.get('search_term')
  search = "%{}%".format(term.lower())
  resp= Venue.query.filter(or_(Venue.name.ilike(search), Venue.city.ilike(search), Venue.state.ilike(search))).all()
  response = {'count':len(resp),'data':resp}
  
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
      #Querying the venue table
  venue = db.session.query(Venue).filter(Venue.id == venue_id).all()
  current_time = datetime.now(timezone.utc)
  data= {}
  completed_shows = []
  future_shows = []
  #looping through columns in venue
  for item in venue:
        upcoming_shows = db.session.query(Show).join(Venue).filter(Show.artist_id==venue_id).filter(Show.show_start_time<datetime.now()).all()   
        past_shows = db.session.query(Show).join(Venue).filter(Show.artist_id==venue_id).filter(Show.show_start_time>datetime.now()).all()
        data.update({
        "id": item.id,
        "name": item.name,
        "genres": item.genres.split(", "),
        "address": item.address,
        "city": item.city,
        "state": item.state,
        "phone": item.phone,
        "website": item.website,
        "facebook_link": item.facebook_link,
        "seeking_talent": item.seeking_talent,
        "seeking_description": item.seeking_description,
        "image_link": item.image_link,
        })
        #ilterating upcoming shows
        for show in upcoming_shows:
            if len(upcoming_shows) == 0:
                  data.update({"upcoming_shows": [],})
            else:
                  artist = db.session.query(Artist.name, Artist.image_link).filter(Artist.id == show.artist_id).one()
                  future_shows.append({
                  "artist_id": show.artist_id,
                  "artist_name": artist.name,
                  "artist_image_link": artist.image_link,
                  "show_start_time": show.show_start_time.strftime('%m/%d/%Y'),
                  })
        #ilterating upcoming Past shows
        for show in past_shows:
            if len(past_shows) == 0:
                  data.update({"past_shows": [],})
            else:
                  artist = db.session.query(Artist.name, Artist.image_link).filter(Artist.id == show.artist_id).one()
                  completed_shows.append({
                  "artist_id": show.artist_id,
                  "artist_name": artist.name,
                  "artist_image_link": artist.image_link,
                  "show_start_time": show.show_start_time.strftime('%m/%d/%Y'),
                  })
        #Adding data
        data.update({"upcoming_shows": future_shows})
        data.update({"past_shows": completed_shows})
        data.update({"past_shows_count": len(past_shows), "upcoming_shows_count": len(upcoming_shows),})
  return render_template('pages/show_venue.html', venue=data)



#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    form = VenueForm()

    # Form validation
    if not form.validate():
        for fieldName, errorMessages in form.errors.items():
            show_form_errors(fieldName, errorMessages)

        return redirect(url_for('create_venue_form'))

    try:
        # Create model
        data = Venue()
        data.name = request.form.get('name')
        data.genres = ', '.join(request.form.getlist('genres'))
        data.address = request.form.get('address')
        data.city = request.form.get('city')
        data.state = request.form.get('state')
        data.phone = request.form.get('phone')
        data.facebook_link = request.form.get('facebook_link')
        data.image_link = request.form.get('image_link')
        data.website = request.form.get('website_link')
        data.seeking_talent = True if request.form.get('seeking_talent')!= None else False
        data.seeking_description = request.form.get('seeking_description')
        # Update DB
        db.session.add(data)
        db.session.commit()
    except Exception:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    # Show banner
    if error:
        abort(400)
        flash('An error occurred. Venue ' + request.form.get('name') + ' could not be listed.')
    if not error:
        flash('Venue ' + request.form.get('name') + ' was successfully listed!')

    return render_template('pages/home.html')



#  Update Venue
#  ----------------------------------------------------------------
@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    data = Venue.query.get(venue_id)
    venue={
      "id": data.id,
      "name": data.name,
      "city": data.city,
      "state": data.state,
      "phone": data.phone,
      "genres": data.genres.split(", "),
      "address": data.address,
      "website": data.website,
      "facebook_link": data.facebook_link,
      "seeking_talent": data.seeking_talent,
      "seeking_description": data.seeking_description,
      "image_link": data.image_link,
    }
    # populated form with values from venue table with ID <venue_id>
    
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
        #First try to see if adding changing the new items works
        try:
            data = Venue()
            data.name = request.form.get('name')
            data.city = request.form.get('city')
            data.state = request.form.get('state')
            data.phone = request.form.get('phone')
            # converting array to string separated by commas
            data.genres = ', '.join(request.form.getlist('genres'))
            data.address = request.form.get('address')
            data.facebook_link = request.form.get('facebook_link')
            data.image_link = request.form.get('image_link')
            data.website = request.form.get('website_link')
            data.seeking_talent = True if request.form.get('seeking_talent')!= None else False
            data.seeking_description = request.form.get('seeking_description')

            #Adding the new edited venue to Db and commiting it
            db.session.add(data)
            db.session.commit()

            flash("Venue " + request.form.get('name') + " was edited successfully")
            
        except:
            db.session.rollback()
            print(sys.exc_info())
            flash("Venue edition unsuccessfully.")
        finally:
            db.session.close()

        return redirect(url_for('show_venue', venue_id=venue_id))


# Delete Venue
#----------------------------------------------------------------------

@app.route("/venues/<venue_id>/delete", methods={"GET"})
def delete_venue(venue_id):
  # This endpoint is responsible for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    error = True
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
        flash("Venue " + venue.name + " was deleted successfully!")
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
        flash("Attempt to delete " + venue.name + "Venue was unsuccessfully.")
    finally:
        db.session.close()
    
    return redirect(url_for("index"))
  
  # Implemented a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage



#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # replaced with real data returned from querying the database
  data=[]
  artists = db.session.query(Artist).order_by('id').all()
  for artist in artists:   
      data.append({
          "id":artist.id,
          "name":artist.name,
          })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  term = request.form.get('search_term')
  search = "%{}%".format(term.lower())
  res= Artist.query.filter(or_(Artist.name.ilike(search), Artist.city.ilike(search), Artist.state.ilike(search))).all()
  response = {'count':len(res),'data':res}
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  artist = db.session.query(Artist).filter(Artist.id == artist_id).all()
  current_time = datetime.now(timezone.utc)
  data= {}
  completed_show = []
  up_coming_show = []
  for item in artist:
        upcoming_shows = db.session.query(Show).join(Venue).filter(Show.artist_id==artist_id).filter(Show.show_start_time<datetime.now()).all()
        past_shows = db.session.query(Show).join(Venue).filter(Show.artist_id==artist_id).filter(Show.show_start_time<datetime.now()).all()
        data.update({
        "id": item.id,
        "name": item.name,
        "city": item.city,
        "state": item.state,
        "phone": item.phone,
        "genres": item.genres.split(", "), #converting string to arrays
        "website": item.website,
        "facebook_link": item.facebook_link,
        "seeking_venue": item.seeking_venue,
        "seeking_description": item.seeking_description,
        "image_link": item.image_link,
        })

        # getting upcoming shows
        for show in upcoming_shows:
            if len(upcoming_shows) == 0:
                  data.update({"upcoming_shows": [],})
            else:
                  venue = db.session.query(Venue.name, Venue.image_link).filter(Venue.id == show.venue_id).one()
                  up_coming_show.append({
                  "venue_id": show.venue_id,
                  "venue_name": venue.name,
                  "venue_image_link": venue.image_link,
                  "show_start_time": show.show_start_time.strftime('%m/%d/%Y'),
                  })
        
        # getting Past shows
        for show in past_shows:
            if len(past_shows) == 0:
                  data.update({"past_shows": [],})
            else:
                  venue = db.session.query(Venue.name, Venue.image_link).filter(Venue.id == show.venue_id).one()
                  completed_show.append({
                  "venue_id": show.venue_id,
                  "venue_name": venue.name,
                  "venue_image_link": venue.image_link,
                  "show_start_time": show.show_start_time.strftime('%m/%d/%Y'),
                  })
        data.update({"upcoming_shows": up_coming_show})
        data.update({"past_shows": completed_show})
        data.update({"past_shows_count": len(past_shows), "upcoming_shows_count": len(upcoming_shows),})
  return render_template('pages/show_artist.html', artist=data)



#  Update Artist
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
      form = ArtistForm()
      data = Artist.query.get(artist_id)
      artist={
        "id": data.id,
        "name": data.name,
        "city": data.city,
        "state": data.state,
        "phone": data.phone,
        "genres": data.genres.split(", "),
        "website_link": data.website,
        "facebook_link": data.facebook_link,
        "seeking_venue": data.seeking_venue,
        "seeking_description": data.seeking_description,
        "image_link": data.image_link,
      }
      # TODO: populate form with fields from artist with ID <artist_id>
      return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # TODO: take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes
    error = False
    try:
      data = Artist.query.get(artist_id)
      data.name = request.form.get('name')
      data.city = request.form.get('city')
      data.state = request.form.get('state')
      data.phone = request.form.get('phone')
      data.genres = ', '.join(request.form.getlist('genres'))
      data.facebook_link = request.form.get('facebook_link')
      data.image_link = request.form.get('image_link')
      data.website = request.form.get('website_link')
      data.seeking_venue = True if request.form.get('seeking_venue')!=None else False
      data.seeking_description = request.form.get('seeking_description')
      db.session.add(data)
      db.session.commit()

      flash("Artist " + request.form.get('name') + " was edited successfully")
      #Note: request.form.get is easier and safer to use than accessing the value directly to handel null cases
    except:
      error = True
      db.session.rollback()
      print(sys.exc_info())
      flash("Attempt to edit " + request.form.get('name') + " Artist was unsuccessfully.")
    finally:
      db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))


#  Create Artist
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    form = ArtistForm()

    # Form validation
    if not form.validate():
        for fieldName, errorMessages in form.errors.items():
            show_form_errors(fieldName, errorMessages)

        return redirect(url_for('create_artist_form'))

    try:
        # Create Artist model
        data = Artist()
        data.name = request.form.get('name')
        data.genres = ', '.join(request.form.getlist('genres'))
        data.address = request.form.get('address')
        data.city = request.form.get('city')
        data.state = request.form.get('state')
        data.phone = request.form.get('phone')
        data.facebook_link = request.form.get('facebook_link')
        data.image_link = request.form.get('image_link')
        data.website = request.form.get('website_link')
        data.seeking_talent = True if request.form.get('seeking_talent')!= None else False
        data.seeking_description = request.form.get('seeking_description')
        # Update DB
        db.session.add(data)
        db.session.commit()
    except Exception:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()

    # Show error banner
    if error:
        abort(400)
        flash('An error occurred. Artist ' + request.form.get('name') + ' could not be listed.')
    if not error:
        flash('Artist ' + request.form.get('name') + ' was successfully listed!')

    return render_template('pages/home.html')



# Delete Artist
#----------------------------------------------------------------------

@app.route('/artists/<artist_id>/delete', methods=['DELETE'])
def delete_artist(artist_id):
  # This endpoint is responsible for taking an artist_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    error = False
    try:
      artist = Artist.query.get(artist_id)
      db.session.delete(artist)
      db.session.commit()
      flash("Artist " + artist.name + " was successfully deleted.")
    except:
      error=True
      db.session.rollback()
      flash("Attempt to delete " + artist.name + " was unsuccessful.")
    finally:
      db.session.close()
      
    return render_template('pages/artists.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  #Declaring an empty array
  data = []
  shows = db.session.query(Show).order_by(desc(Show.show_start_time)).all()
  for show in shows:
        artist = db.session.query(Artist.name, Artist.image_link).filter(Artist.id == show.artist_id).one()
        venue = db.session.query(Venue.name).filter(Venue.id == show.venue_id).one()
        data.append({
          "venue_id": show.venue_id,
          "venue_name": venue.name,
          "artist_id": show.artist_id,
          "artist_name":artist.name,
          "artist_image_link": artist.image_link,
          "show_start_time": show.show_start_time.strftime('%m/%d/%Y')
        })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead
  error=False
  try:
    data = Show()
    data.artist_id = request.form.get('artist_id')
    data.venue_id = request.form.get('venue_id')
    data.show_start_time = request.form.get('show_start_time')
    db.session.add(data)
    db.session.commit()
  except:
    error=True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    flash('Show was successfully listed!')
  else:
    flash('An error occurred while trying to create Show.')
    abort(500)
  return render_template('pages/home.html')
  # on successful db insert, flash success
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
