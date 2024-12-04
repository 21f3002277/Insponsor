from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, cast, Integer

db = SQLAlchemy()  # instance of SQLAlchemy

class User_Info(db.Model):
    __tablename__ = 'user_info'
    userid = db.Column(db.String(), primary_key=True)
    password = db.Column(db.String(), nullable=False)
    role = db.Column(db.String(), default='influencer')
    status = db.Column(db.String(), default='Active', nullable=False)

class Flagged(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(), db.ForeignKey('user_info.userid'))
    strikes = db.Column(db.String(), db.ForeignKey('campaign.campaign_id'))


class Influencer(db.Model):
    __tablename__ = 'influencer'
    influencer_id = db.Column(db.String(), db.ForeignKey('user_info.userid'), primary_key=True)
    username = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(), nullable=False)
    mobile_no = db.Column(db.String(10), unique=True)
    profile_photo = db.Column(db.String(), nullable=True, default='/static/img/blank-profile-picture-973460_1280.png')
    address = db.Column(db.String(), nullable=True)
    bio = db.Column(db.String())
    niche_id = db.Column(db.Integer, db.ForeignKey('niche.niche_id'))

    user_info = db.relationship('User_Info', backref=db.backref('influencer_info', uselist=False))
    campaigns = db.relationship('Campaign', backref='influencer', lazy=True)
    ratings = db.relationship('Rating', backref='influencer', lazy=True)
    reviews = db.relationship('Review', backref='influencer', lazy=True)
    invoices = db.relationship('Invoice', backref='influencer', lazy=True)  # unique backref
    ads_requests = db.relationship('Ads_Request', backref='influencer', lazy=True)
    recommend = db.relationship('Recommend', backref='influencer', lazy=True)
    social_handle = db.relationship('Social_media', backref='influencer', lazy=True)


class Sponsor(db.Model):
    __tablename__ = 'sponsor'
    sponsor_id = db.Column(db.String(), db.ForeignKey('user_info.userid'), primary_key=True)
    username = db.Column(db.String(), nullable=False)
    job_title = db.Column(db.String())
    company = db.Column(db.String())
    email = db.Column(db.String(), nullable=False)
    mobile_no = db.Column(db.String(10), unique=True)
    address = db.Column(db.String(), nullable=True)
    profile_photo = db.Column(db.String(), nullable=True, default='/static/img/blank-profile-picture-973460_1280.png')
    user_info = db.relationship('User_Info', backref=db.backref('sponsor_info', uselist=False))
    ads_requests = db.relationship('Ads_Request', backref='sponsor', lazy=True)
    social_handle = db.relationship('Social_media', backref='sponsor', lazy=True)
    invoices = db.relationship('Invoice', backref='sponsor', lazy=True)  # unique backref


class Niche(db.Model):
    __tablename__ = 'niche'
    niche_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)

    influencers = db.relationship('Influencer', lazy=True)


class Campaign(db.Model):
    __tablename__ = 'campaign'
    campaign_id = db.Column(db.String(), primary_key=True)
    campaign_name = db.Column(db.String())
    description = db.Column(db.String(), nullable=False)
    budget = db.Column(db.String(), nullable=False)
    visibility = db.Column(db.String(), nullable=False, default='Public')
    start_date = db.Column(db.Date(), nullable=False)
    end_date = db.Column(db.Date(), nullable=False)
    sponsor_id = db.Column(db.String(), db.ForeignKey('sponsor.sponsor_id'))
    influencer_id = db.Column(db.String(), db.ForeignKey('influencer.influencer_id'))
    niche = db.Column(db.Integer(), db.ForeignKey('niche.niche_id'))
    status = db.Column(db.String(), nullable=False, default='Pending')

    ads_requests = db.relationship('Ads_Request', backref='campaign', cascade="all, delete-orphan", lazy=True)
    ratings = db.relationship('Rating', backref='campaign', lazy=True)
    reviews = db.relationship('Review', backref='campaign', lazy=True)
    invoices = db.relationship('Invoice', backref='campaign', lazy=True)  # unique backref

    def calculate_cost_per_day(self):
        duration = (self.end_date - self.start_date).days
        if duration > 0:
            return float(self.budget) / duration
        return 0


class Ads_Request(db.Model):
    __tablename__ = 'ads_request'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    campaign_id = db.Column(db.String(), db.ForeignKey('campaign.campaign_id'), nullable=False)
    influencer_id = db.Column(db.String(), db.ForeignKey('influencer.influencer_id'))
    sponsor_id = db.Column(db.String(), db.ForeignKey('sponsor.sponsor_id'))
    status = db.Column(db.String(), nullable=False, default='Pending')
    sender = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    budget = db.Column(db.Integer())


class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    influencer_id = db.Column(db.String(), db.ForeignKey('influencer.influencer_id'))
    campaign_id = db.Column(db.String(), db.ForeignKey('campaign.campaign_id'))
    rating = db.Column(db.Integer(), nullable=False)


class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    influencer_id = db.Column(db.String(), db.ForeignKey('influencer.influencer_id'))
    sponsor_id = db.Column(db.String(), db.ForeignKey('sponsor.sponsor_id'))
    campaign_id = db.Column(db.String(), db.ForeignKey('campaign.campaign_id'))
    review = db.Column(db.String(), nullable=False)
    sponsor = db.relationship('Sponsor', backref='reviews')


class Recommend(db.Model):
    __tablename__ = 'recommend'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    influencer_id = db.Column(db.String(), db.ForeignKey('influencer.influencer_id'))
    sponsor_id = db.Column(db.String(), db.ForeignKey('sponsor.sponsor_id'))


class Social_media(db.Model):
    __tablename__ = 'social_media'
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    influencer_id = db.Column(db.String(), db.ForeignKey('influencer.influencer_id'), nullable=True)
    sponsor_id = db.Column(db.String(), db.ForeignKey('sponsor.sponsor_id'), nullable=True)
    platform = db.Column(db.String(), nullable=False)
    link = db.Column(db.String())


class Invoice(db.Model):
    __tablename__ = 'invoice'
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.String(), db.ForeignKey('campaign.campaign_id'), nullable=False)
    influencer_id = db.Column(db.String(), db.ForeignKey('influencer.influencer_id'), nullable=False)
    sponsor_id = db.Column(db.String(), db.ForeignKey('sponsor.sponsor_id'), nullable=False)
    payment_amount = db.Column(db.Float, nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Unpaid')


class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount_paid = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(), nullable=False)
    payment_status = db.Column(db.String(50), default='Pending')
