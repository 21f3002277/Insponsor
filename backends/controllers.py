from flask import Flask, render_template, request, redirect, url_for, flash, session,json,jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
from flask import current_app as app # for current running application
from .models import *  
from datetime import datetime, timedelta
import pytz


# Helper functions
def validate_passwords(password, confirm_password):
    if password != confirm_password:
        flash('Passwords do not match.')
        return False
    return True

def validate_fields(required_fields):
    for field in required_fields:
        if not field:
            flash('All fields are required.')
            return False
    return True

def time_greeting():
    ist = pytz.timezone('Asia/Kolkata')

    current_time_ist = datetime.now(ist)
    current_hour = current_time_ist.hour

    if 5 <= current_hour < 12:
        greeting = "Morning"
    elif 12 <= current_hour < 18:
        greeting = "Afternoon"
    elif 18 <= current_hour < 21:
        greeting = "Evening"
    else:
        greeting = "Night"

    return greeting

def earnings24(id):
    last_24hrs = datetime.now() - timedelta(hours=24)
    
    total_earnings = (db.session.query(func.sum(Payment.amount_paid)
                                       .label('total_amount')).join(Invoice,Payment.invoice_id == Invoice.id)
                                       .filter(Invoice.influencer_id == id,  Payment.payment_date >= last_24hrs)
                                       .scalar())
    return total_earnings or 0

def spendings24(id):
    last_24hrs = datetime.now() - timedelta(hours=24)
    
    total_spendings = (db.session.query(func.sum(Payment.amount_paid)
                                       .label('total_amount')).join(Invoice, Payment.invoice_id == Invoice.id)
                                       .filter(Invoice.sponsor_id == id,  Payment.payment_date >= last_24hrs)
                                       .scalar())
    return total_spendings or 0

def campaign_no():
    last_campaign = db.session.query(Campaign).order_by(cast(func.substr(Campaign.campaign_id, 10), Integer).desc()).first()
    if last_campaign is None:
        campaigns_no = "Campaign_1"
    else:
        c_id = last_campaign.campaign_id
        num = int(c_id[9:])
        campaigns_no = "Campaign_" + str(num+1)
    return campaigns_no
    
def progress_time(s_date, e_date):
    start_date = date_con(s_date)
    end_date = date_con(e_date)
    current_date = datetime.now()

    total_duration = end_date - start_date
    elapsed_time = current_date - start_date

    p = (elapsed_time / total_duration) * 100
    return p

def auth_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Check if the user is logged in by checking the session
        if 'user_id' not in session:
            flash('You need to log in to access this page.', 'warning')
            return redirect(url_for('User_login'))
        return func(*args, **kwargs)
    
    return decorated_function

def date_con(d):
    d = datetime.strptime(d, "%Y-%m-%d").date()
    return d

def flag_id(id):
    flagged_count = Flagged.query.filter_by(user_id=id).count() or 0
    if int(flagged_count) > 1:
        login = User_Info.query.filter_by(userid=id).first()
        print()
        login.status ='Flagged'
        db.session.commit()
        return True
    else:
        return False


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")

@app.route("/login", methods=["GET", "POST"])
def User_login():
    if request.method == "POST":
        user_id = request.form.get("uname")
        password = request.form.get("pwd")
        
        if not user_id or not password:
            flash('Both fields are required', 'error')
            return render_template("login.html")
        
        user = User_Info.query.filter_by(userid=user_id).first()
        if (user and check_password_hash(user.password, password)):
            if user.status=='Active':
                session['user_id'] = user.userid
                session['role'] = user.role
                flash('Login successful!', 'success')

                if user.role == 'sponsor':
                    return redirect(url_for('sponsor_dashboard', user_id=user_id))
                elif user.role == 'influencer':
                    return redirect(url_for('influencer_dashboard', user_id=user_id))
                elif user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Unauthorized role.')
                    return redirect(url_for('User_login'))
            else:
                return(url_for('User_login'))
        else:
            flash('Invalid UserID or Password', 'error')
            return render_template("login.html")
    
    return render_template("login.html")

@app.route("/registerInfluencer", methods=["GET", "POST"])
def influencer_register():
    niches = Niche.query.all()
    if request.method == "POST":
        user_id = request.form.get("U_Id")
        f_name = request.form.get("F_name")
        password = request.form.get("pwd")
        c_password = request.form.get("C_pwd")
        niche_name = request.form.get("niche")
        email = request.form.get("email")
        mobile = request.form.get("mobile")

        if not validate_fields([user_id, password, c_password, f_name, niche_name]):
            return render_template("register_influencer.html", niches=niches)
        
        if not validate_passwords(password, c_password):
            return render_template("register_influencer.html", niches=niches)

        if User_Info.query.filter_by(userid=user_id).first():
            flash('UserID already exists!')
            return render_template("register_influencer.html", niches=niches)
        
        niche = Niche.query.filter_by(name=niche_name).first()
        if not niche:
            flash('Selected niche does not exist.')
            return render_template("register_influencer.html", niches=niches)
        
        hashed_password = generate_password_hash(password)
        new_user = User_Info(userid=user_id, password=hashed_password, role="influencer")
        userdetails = Influencer(influencer_id=user_id, username=f_name, niche_id=niche.niche_id, email=email, mobile_no=mobile)

        db.session.add(new_user)
        db.session.add(userdetails)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for("User_login"))
    
    return render_template("register_influencer.html", niches=niches)

@app.route("/registerSponsor", methods=["GET", "POST"])
def sponsor_register():
    if request.method == "POST":
        user_id = request.form.get("U_Id")
        f_name = request.form.get("F_name")
        password = request.form.get("pwd")
        c_password = request.form.get("C_pwd")
        company_name = request.form.get("C_name")
        job_title = request.form.get("J_title")
        email = request.form.get("email")
        mobile = request.form.get("mobile")
        profile_photo = request.files.get('photo')

        if not validate_fields([user_id, password, c_password, f_name, company_name, job_title]):
            return render_template("register_sponsor.html")
        
        if not validate_passwords(password, c_password):
            return render_template("register_sponsor.html")

        if User_Info.query.filter_by(userid=user_id).first():
            flash('UserID already exists!')
            return render_template("register_sponsor.html")
        
        hashed_password = generate_password_hash(password)
        new_user = User_Info(userid=user_id, password=hashed_password, role="sponsor")
        db.session.add(new_user)
        
        # Handle profile picture upload
        profile_photo = request.files.get('photo')
        if profile_photo and allowed_file(profile_photo.filename):
            filename = secure_filename(profile_photo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_photo.save(filepath)
            photos =f'/{filepath}'
            print(photos)
            userdetails = Sponsor(sponsor_id=user_id, username=f_name, job_title=job_title, company=company_name, email=email,
                               mobile_no=mobile, profile_photo = photos )
            db.session.add(userdetails)
            db.session.commit()

        # Handle social media links
        social_media_platforms = ['instagram', 'facebook', 'youtube', 'linkedin']
        try:
            for platform in social_media_platforms:
                link = request.form.get(platform)
                if link and link.strip():  
                    new_social_media = Social_media(sponsor_id=user_id,platform=platform,link=link)
                    db.session.add(new_social_media)
        except SQLAlchemyError as e:
            # Rollback changes in case of an error and log the exception
            db.session.rollback()
            print(f"Database error: {e}")

        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for("User_login"))
    
    return render_template("register_sponsor.html")

@app.route("/logout")
@auth_required
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('You have been logged out.')
    return redirect(url_for('User_login'))

@app.route("/sponsor/<user_id>", methods=["GET", "POST"])
@auth_required
def sponsor_dashboard(user_id):
    greeting = time_greeting()
    niches = Niche.query.all()
    influencers = Influencer.query.all()
    campaigns = Campaign.query.all()
    sponsors = Sponsor.query.get(user_id)

    spends = spendings24(user_id)
    
    activeCampaign_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.status == 'Accepted', Campaign.sponsor_id == user_id).scalar() or 0
    completedCampaign_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.status == 'Completed', Campaign.sponsor_id == user_id).scalar() or 0

    active_campaigns = db.session.query(Campaign, Influencer, Sponsor).join(Sponsor, Campaign.sponsor_id == Sponsor.sponsor_id).join(Influencer, Campaign.influencer_id == Influencer.influencer_id).filter(Campaign.sponsor_id == user_id, Campaign.status == 'Accepted').all()
    flagged_campaigns = db.session.query(Campaign, Influencer, Sponsor).join(Sponsor, Campaign.sponsor_id == Sponsor.sponsor_id).join(Influencer, Campaign.influencer_id == Influencer.influencer_id).filter(Campaign.sponsor_id == user_id, Campaign.status == 'Flagged').all()
    ads_requests_sponsor = db.session.query(Ads_Request, Campaign, Sponsor).join(Campaign, Ads_Request.campaign_id == Campaign.campaign_id).join(Sponsor, Ads_Request.sponsor_id == Sponsor.sponsor_id).filter(Ads_Request.sponsor_id == user_id, Ads_Request.status.in_(['Pending', 'Rejected']), Campaign.status=='Pending', Ads_Request.sender == 'Sponsor').all()
    ads_requests_influencer = db.session.query(Ads_Request, Campaign, Influencer).join(Campaign, Ads_Request.campaign_id == Campaign.campaign_id).join(Influencer, Ads_Request.influencer_id == Influencer.influencer_id).filter(Ads_Request.sponsor_id == user_id, Ads_Request.status == 'Pending', Ads_Request.sender == 'Influencer').all()
    nonActive_campaigns = db.session.query(Campaign, Influencer, Sponsor).join(Influencer, Campaign.influencer_id == Influencer.influencer_id).join(Sponsor, Campaign.sponsor_id == Sponsor.sponsor_id).filter(Campaign.sponsor_id == user_id, Campaign.status.in_(['Completed', 'Payment'])).all()
    all_campaign = Campaign.query.filter_by(sponsor_id=user_id).all()
    filtered_influencers = {}
    for campaign in all_campaign:
        influencers = Influencer.query.filter_by(niche_id=campaign.niche).all()
        filtered_influencers[campaign.campaign_id] = influencers

    return render_template("sponsor_dashboard.html", adsRequests=ads_requests_sponsor,uname=user_id,greeting=greeting,
                           niches=niches,active_campaigns=active_campaigns,completed_campaigns=nonActive_campaigns,
                           complete_campaign_no=completedCampaign_no,adsRequests_influencer=ads_requests_influencer,
                           campaigns=campaigns,influencers=influencers,activeCampaign_no=activeCampaign_no,
                           completedCampaign_no=completedCampaign_no, flagged_campaigns=flagged_campaigns,spends=spends,
                           filtered_influencers=filtered_influencers)

@app.route("/influencer/<user_id>", methods=["GET", "POST"])
@auth_required
def influencer_dashboard(user_id):
    greeting = time_greeting()
    influencer = Influencer.query.get(user_id)
    
    if not influencer:
        flash('Influencer not found.')
        return redirect(url_for('User_login'))

    earns = earnings24(user_id)
    
    activeCampaign_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.status == 'Accepted', Campaign.influencer_id == user_id).scalar() or 0
    completedCampaign_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.status == 'Completed', Campaign.influencer_id == user_id).scalar() or 0
    
    if completedCampaign_no == 0:
        ratings = 0
    else:
        ratings = round(sum([rate.rating for rate in influencer.ratings]) / completedCampaign_no, 1)
    
    active_campaign = db.session.query(Campaign, Influencer, Sponsor).join(Influencer, Campaign.influencer_id == Influencer.influencer_id).join(Sponsor, Campaign.sponsor_id == Sponsor.sponsor_id).filter(Campaign.influencer_id == user_id, Campaign.status == 'Accepted').all()

    flagged_campaign = db.session.query(Campaign, Influencer, Sponsor).join(Influencer, Campaign.influencer_id == Influencer.influencer_id).join(Sponsor, Campaign.sponsor_id == Sponsor.sponsor_id).filter(Campaign.influencer_id == user_id, Campaign.status == 'Flagged').all()

    print(flagged_campaign)
    
    adsRequests = db.session.query(Ads_Request, Campaign, Sponsor).join(Campaign, Ads_Request.campaign_id == Campaign.campaign_id).join(Sponsor, Ads_Request.sponsor_id == Sponsor.sponsor_id).filter(Ads_Request.influencer_id == user_id, Ads_Request.status == 'Pending', Ads_Request.sender == 'Sponsor').all()
    
    completed_campaigns = db.session.query(Campaign, Influencer, Sponsor).join(Influencer, Campaign.influencer_id == Influencer.influencer_id).join(Sponsor, Campaign.sponsor_id == Sponsor.sponsor_id).filter(Campaign.influencer_id == user_id, Campaign.status == 'Completed').all()
    
    return render_template("influencer_dashboard.html", adsRequests=adsRequests,uname=user_id,greeting=greeting,
                           niches=Niche.query.all(),active_campaign=active_campaign,completed_campaigns=completed_campaigns,
                           completedCampaign_no=completedCampaign_no,earns=earns,activeCampaign_no=activeCampaign_no,
                           ratings=ratings, flagged_campaign=flagged_campaign)

@app.route("/adminDashboard", methods=["GET", "POST"])
@auth_required
def admin_dashboard():
    greeting = time_greeting()
    all_campaigns = db.session.query(Campaign).filter(Campaign.status !='Completed').all()
    campaigns = Campaign.query.all()
    flagged_campaigns = db.session.query(Campaign).filter(Campaign.status=='Flagged').all()
    ad_requests_data = {}
    campaign_data = {}

    for campaign in campaigns:
        pending_count = Ads_Request.query.filter_by(campaign_id=campaign.campaign_id, status='Pending').count()
        approved_count = Ads_Request.query.filter_by(campaign_id=campaign.campaign_id, status='Approved').count()
        rejected_count = Ads_Request.query.filter_by(campaign_id=campaign.campaign_id, status='Rejected').count()
        total_invoiced_amount = db.session.query(func.sum(Invoice.payment_amount)).filter_by(campaign_id=campaign.campaign_id).scalar() or 0
        total_paid_amount = db.session.query(func.sum(Payment.amount_paid)).join(Invoice).filter(Invoice.campaign_id == campaign.campaign_id).scalar() or 0
        pending_invoices = total_invoiced_amount - total_paid_amount
        print(ad_requests_data)

        ad_requests_data[campaign.campaign_id] = {
            'pending': pending_count,
            'approved': approved_count,
            'rejected': rejected_count 
        }
        campaign_data[campaign.campaign_id] = {
            'invoiced_amount': total_invoiced_amount,
            'paid_amount': total_paid_amount,
            'pending_amount': pending_invoices
        }
    print(ad_requests_data)

    total_ads_requests = db.session.query(func.count(Ads_Request.id)).scalar()
    pending_ads_requests = db.session.query(func.count(Ads_Request.id)).filter(Ads_Request.status == 'Pending').scalar()
    approved_ads_requests = db.session.query(func.count(Ads_Request.id)).filter(Ads_Request.status == 'Approved').scalar()
    rejected_ads_requests = db.session.query(func.count(Ads_Request.id)).filter(Ads_Request.status == 'Rejected').scalar()



    return render_template(
        "admin_dashboard.html", 
        greeting=greeting, all_campaigns=all_campaigns, flagged_campaigns=flagged_campaigns,campaigns=campaigns, 
        ad_requests_data =ad_requests_data,campaign_data=campaign_data, total_ads_requests=total_ads_requests,
        pending_ads_requests=pending_ads_requests,approved_ads_requests=approved_ads_requests,
        rejected_ads_requests=rejected_ads_requests
    )

@app.route("/sponsor/campaign/<user_id>", methods=["GET", "POST"])
@auth_required
def SponsorCampaign(user_id):         ########## Public Campaign
    campaigns_no = campaign_no()
        
    all_campaign = Campaign.query.filter_by(sponsor_id=user_id).all()
    total_items = len(all_campaign)
    items_per_page = 8
    current_page = int(request.args.get('page', 1))
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # Get campaigns for the current page
    campaigns_query = Campaign.query.filter_by(sponsor_id=user_id).offset((current_page - 1) * items_per_page).limit(items_per_page)
    all_campaigns = campaigns_query.all()

    # Handle form submission
    if request.method == 'POST':
        campaign_id = request.form.get('campaign_Id')
        campaign_name = request.form.get('campaign_name')
        niche_id = request.form.get('niche')
        description = request.form.get('description')
        budget = request.form.get('budget')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:

            return redirect(url_for('SponsorCampaign', user_id=user_id))

        if not all([campaign_id, campaign_name, niche_id, description, budget, start_date, end_date]):
            return redirect(url_for('SponsorCampaign', user_id=user_id))  

        try:
            new_campaign = Campaign(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                description=description,
                budget=budget,
                visibility='Public',  
                start_date=start_date,
                end_date=end_date,
                sponsor_id=user_id,  
                niche=niche_id,
                status='Pending'  
            )
            db.session.add(new_campaign)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
 

        return redirect(url_for('SponsorCampaign', user_id=user_id))  
    
    # Prepare data for rendering
    niches = Niche.query.all()
    filtered_influencers = {}
    for campaign in all_campaign:
        influencers = Influencer.query.filter_by(niche_id=campaign.niche).all()
        filtered_influencers[campaign.campaign_id] = influencers

    return render_template("campaign.html", campaigns_id=campaigns_no, niches=niches, uname=user_id, 
                           campaign_records=all_campaigns, filtered_influencers=filtered_influencers, 
                           total_pages=total_pages, current_page=current_page)

@app.route("/sponsor/campaign/<user_id>/UpdateCampaign", methods=["POST"])
@auth_required
def update_campaign(user_id):
    if request.method == "POST":
        C_id = request.form.get("C_id")
        campaign_name = request.form.get("campaign_name")
        description = request.form.get("description")
        budget = request.form.get("budget")
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        I_id = request.form.get('P_Influencer')

        campaign = Campaign.query.filter_by(campaign_id=C_id).first()
        if I_id :
            adRequest = Ads_Request(campaign_id=C_id, influencer_id=I_id, sponsor_id=user_id, status='Pending', 
                                        sender='Sponsor', description=description, budget=budget)
            db.session.add(adRequest)
            campaign.influencer_id = I_id
            db.session.commit()

        campaign.campaign_name = campaign_name
        campaign.description = description
        campaign.budget = budget
        campaign.start_date = date_con(start_date)
        campaign.end_date = date_con(end_date)
        db.session.commit()
        return redirect(url_for('SponsorCampaign', user_id=user_id))
    
@app.route("/sponsor/campaign/<user_id>/delete", methods=["POST"])
@auth_required
def delete_campaign(user_id):
    campaign_id = request.form.get("C_id")
    campaign = Campaign.query.filter_by(campaign_id=campaign_id).first()
    if campaign:

        Ads_Request.query.filter_by(campaign_id=campaign_id).delete()
        Rating.query.filter_by(campaign_id=campaign_id).delete()
        Review.query.filter_by(campaign_id=campaign_id).delete()
        db.session.delete(campaign)
        db.session.commit()
        return redirect(url_for('SponsorCampaign', user_id=user_id))
           
@app.route("/sponsor/campaign/<user_id>/adsRequest", methods=[ "POST"])
def addRequest(user_id):
    if request.method == "POST":
        C_id = request.form.get("c_id")
        influ_id = request.form.get('P_Influencer')
        budget = request.form.get('budget')
        description = request.form.get('description')

        new_adRequest = Ads_Request(campaign_id=C_id, influencer_id=influ_id, sponsor_id=user_id, status='Pending', 
                                        sender='Sponsor', description=description, budget=budget)
        db.session.add(new_adRequest)
        db.session.commit()
        flash('Request sent successfully!', 'info')
        return redirect(url_for('SponsorCampaign', user_id=user_id))
    
@app.route('/influencer/<user_id>/search/campaigns', methods=["GET", "POST"])
def public_search_campaign(user_id):
    query = db.session.query(Campaign, Sponsor).join(Sponsor, Campaign.sponsor_id == Sponsor.sponsor_id).filter(Campaign.visibility == 'Public', Campaign.status == 'Pending')
    total_items = query.count()
    items_per_page = 8
    current_page = int(request.args.get('page', 1))
    total_pages = (total_items + items_per_page - 1) // items_per_page
    campaigns_query = query.offset((current_page - 1) * items_per_page).limit(items_per_page)
    public_campaigns = campaigns_query.all()
    
    requests = Ads_Request.query.filter_by(influencer_id=user_id, sender='Influencer').all()
    requested_campaigns = [ads.campaign_id for ads in requests]
    niches = Niche.query.all()

    print(requested_campaigns)

    current_url = request.url
    if request.method=="POST":
        C_id = request.form.get("C_id")
        s_id = request.form.get("s_id")
        terms_descri = request.form.get("Terms_descri") or request.form.get("descri")
        influencer_budget = request.form.get("Influencer_budget") or request.form.get("budget")

        addRequest=Ads_Request(campaign_id=C_id, influencer_id=user_id, sponsor_id=s_id, sender ='Influencer', 
                               description= terms_descri, budget= influencer_budget)
        db.session.add(addRequest)
        db.session.commit()
        flash('Request sent successfully!', 'info')
        return redirect(url_for('public_search_campaign', user_id=user_id))
    return render_template("find.html",uname=user_id, current_url=current_url, public_campaigns = public_campaigns, 
                           requested_campaigns=requested_campaigns, current_page=current_page,total_pages=total_pages,niches=niches)

@app.route('/influencer/<user_id>/campaigns/<campaign_id>/adsrequest',methods=["POST"])
def influencer_request(user_id, campaign_id):
        s_id = request.form.get("S_id")
        terms_descri = request.form.get("Terms_descri")
        influencer_budget = request.form.get("Influencer_budget")

        adsRequest = db.session.query(Ads_Request).filter(Ads_Request.campaign_id==campaign_id, Ads_Request.sponsor_id==s_id, Ads_Request.influencer_id==user_id).first()
        if adsRequest :
            adsRequest.description=terms_descri
            adsRequest.budget=influencer_budget
            adsRequest.sender='Influencer'
            db.session.commit()
            flash('Request sent successfully!', 'info')
            return redirect(url_for('influencer_dashboard', user_id=user_id))
        
@app.route('/sponsor/<user_id>/campaign/<campaign_id>/adsrequest/accept',methods=["POST"])
def sponsor_acceptRequest(user_id, campaign_id):
    I_id = request.form.get('I_id')
    N_budget = request.form.get('N_budget')
    N_descri = request.form.get('N_descri')
    campaign = db.session.query(Campaign).filter(Campaign.campaign_id==campaign_id, Campaign.sponsor_id==user_id).first()
    if campaign:
        campaign.status = "Accepted"
        campaign.influencer_id = I_id
        campaign.budget = N_budget
        campaign.description = N_descri
        for requests in campaign.ads_requests:
            if requests.influencer_id == I_id:
                requests.status = "Accepted"
                db.session.commit()
            else:
                requests.status='Rejected'
        flash('Request successfully accepted')
        return redirect(url_for('sponsor_dashboard', user_id=user_id))

@app.route('/sponsor/<user_id>/campaign/<campaign_id>/adsrequest/reject',methods=["POST"])
def sponsor_rejectRequest(user_id, campaign_id):
    I_id = request.form.get('I_id')
    adsRequest = db.session.query(Ads_Request).filter(Ads_Request.campaign_id==campaign_id, Ads_Request.sponsor_id==user_id, Ads_Request.influencer_id==I_id).first()
    if adsRequest:
        adsRequest.status='Rejected'
        db.session.commit()
        flash('Request rejected successfully!', 'info')
        return redirect(url_for('sponsor_dashboard', user_id=user_id))
    
@app.route('/sponsor/<user_id>/campaign/<campaign_id>/adsrequest/edit',methods=["POST"])
def sponsor_editRequest(user_id, campaign_id):
    P_Influ = request.form.get('P_Influ')
    P_Influ_new =request.form.get('P_Influ_new')
    budget = request.form.get('budget')
    description = request.form.get('description')


    adsRequest = db.session.query(Ads_Request).filter(Ads_Request.campaign_id==campaign_id, Ads_Request.sponsor_id==user_id, Ads_Request.influencer_id==P_Influ).first()
    print(P_Influ)
    print(P_Influ_new)
    if adsRequest:
        if P_Influ_new:
            adsRequest.influencer_id=P_Influ_new
        adsRequest.budget=budget
        adsRequest.description=description
        adsRequest.status='Pending'
        db.session.commit()
        flash('Request updated successfully!', 'info')
        return redirect(url_for('sponsor_dashboard', user_id=user_id))
    
@app.route('/sponsor/<user_id>/campaign/<campaign_id>/adsrequest/delete',methods=["POST"])
def sponsor_deleteRequest(user_id, campaign_id):
    I_id = request.form.get('I_id')
    adsRequest = db.session.query(Ads_Request).filter(Ads_Request.campaign_id==campaign_id, Ads_Request.sponsor_id==user_id, Ads_Request.influencer_id==I_id).first()
    campaign = Campaign.query.get(campaign_id)
    if campaign.status == 'Accepted':
        campaign.status == 'Pending'
        db.session.commit()
    if adsRequest:
        db.session.delete(adsRequest)
        db.session.commit()
        flash('Request deleted successfully!', 'info')
        return redirect(url_for('sponsor_dashboard', user_id=user_id))
    
@app.route('/influencer/<user_id>/campaign/<campaign_id>/adsrequest/accept',methods=["POST"])
def influencer_acceptRequest(user_id, campaign_id):
    S_id = request.form.get('S_id')
    campaign = Campaign.query.get(campaign_id)

    if campaign:
        ads = db.session.query(Ads_Request).filter(Ads_Request.sponsor_id==S_id, Ads_Request.campaign_id==campaign_id).all()
        print(ads)
        for requests in ads:
            if requests.influencer_id == user_id:
                requests.status = 'Accepted'
            else:
                requests.status='Rejected'
        campaign.status = "Accepted"
        campaign.influencer_id = user_id
        db.session.commit()
        flash('Request accepted successfully!', 'info')
        return redirect(url_for('influencer_dashboard', user_id=user_id))

@app.route('/influencer/<user_id>/campaign/<campaign_id>/adsrequest/reject',methods=["POST"])
def influencer_rejectRequest(user_id, campaign_id):
    adsRequest = db.session.query(Ads_Request).filter(Ads_Request.campaign_id==campaign_id, Ads_Request.influencer_id==user_id, Ads_Request.influencer_id==user_id).first()
    if adsRequest:
        adsRequest.status='Rejected'
        adsRequest.sender='Sponsor'
        db.session.commit()
        flash('Request rejected successfully!', 'info')
        return redirect(url_for('influencer_dashboard', user_id=user_id))

@app.route('/influencer/campaign/<user_id>/completed', methods = ["POST"])
def complete_campaign(user_id):
    campaign_id = request.form.get("C_id")
    sponsor_id = request.form.get("S_id")
    payment_amount = request.form.get('budget')
    campaign = Campaign.query.filter_by(campaign_id=campaign_id).first()
    if campaign:
        campaign.status = "Payment"
        db.session.commit()

        new_invoice = Invoice(campaign_id=campaign_id,influencer_id=user_id,sponsor_id=sponsor_id, 
                              payment_amount=float(payment_amount),invoice_date=datetime.utcnow(),status='Unpaid')
        db.session.add(new_invoice)
        db.session.commit()
        return redirect(url_for('influencer_dashboard', user_id=user_id))
    
@app.route('/rating', methods=['POST'])
def rating():
    if request.method == 'POST':
        C_id = request.form.get('C_id')
        S_id = request.form.get('S_id')
        I_id = request.form.get('I_id')
        R_score = request.form.get('rating')
        campaign = Campaign.query.get(C_id)
        rate = Rating(campaign_id=C_id, influencer_id=I_id, rating=R_score)
        db.session.add(rate)
        db.session.commit()
        return redirect(url_for('sponsor_dashboard', user_id=S_id))
    
@app.route('/review', methods=['POST'])
def reviews():
    if request.method == "POST":
        C_id = request.form.get('C_id')
        S_id = request.form.get('S_id')
        I_id = request.form.get('I_id')
        review = request.form.get('review')
        reviewing = Review(influencer_id = I_id, campaign_id=C_id, sponsor_id=S_id, review=review)
        db.session.add(reviewing)
        db.session.commit()
        return redirect(url_for('sponsor_dashboard', user_id=S_id))
    
@app.route("/sponsor/<user_id>/searchInfluencer", methods=["GET", "POST"])
@auth_required
def influencers_search(user_id):
    niches = Niche.query.all()
    campaign_id = campaign_no()

    all_influencer = Influencer.query.all()
    total_items = len(all_influencer)
    items_per_page = 8
    current_page = int(request.args.get('page', 1))
    total_pages = (total_items + items_per_page - 1) // items_per_page
    influencers_query = Influencer.query.offset((current_page - 1) * items_per_page).limit(items_per_page)
    all_influencers = influencers_query.all()

    current_url = request.url
    for influencer in all_influencers:
        influencer.average_rating = db.session.query(func.avg(Rating.rating)).filter(Rating.influencer_id == influencer.influencer_id).scalar() or 0
        influencer.review_count = db.session.query(func.count(Review.id)).filter(Review.influencer_id == influencer.influencer_id).scalar() or 0
        influencer.recommend_count = db.session.query(func.count(Recommend.id)).filter(Recommend.influencer_id ==influencer.influencer_id).scalar() or 0

    if request.method =="POST":
        C_id = request.form.get("campaign_Id")
        campaigns = Campaign.query.filter_by(campaign_id=C_id).first()
        influ_id = request.form.get('P_Influencer')
        if not campaigns:
            Campaign_name = request.form.get("campaign_name")
            niche = request.form.get('niche')
            description = request.form.get('description')
            budget = request.form.get('budget')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
        
            new_campaign = Campaign(campaign_id=C_id, campaign_name=Campaign_name, description=description, 
                                visibility='Private' , sponsor_id=user_id, influencer_id=influ_id, niche=niche, 
                                budget=budget, start_date = date_con(start_date), end_date = date_con(end_date))
            db.session.add(new_campaign)
            db.session.commit()
            new_adRequest = Ads_Request(campaign_id=C_id, influencer_id=influ_id, sponsor_id=user_id, status='Pending', 
                                        sender='Sponsor', description=description, budget=budget)
            db.session.add(new_adRequest)
            db.session.commit()
            return redirect(url_for('influencers_search', user_id= user_id, page=current_page))

        else:
            new_adRequest = Ads_Request(campaign_id=campaign_id, influencer_id=influ_id, sponsor_id=user_id, status='Pending', sender='Sponsor', description=description, budget=budget)
            db.session.add(new_adRequest)
            db.session.commit()
            return redirect(url_for('influencers_search', user_id= user_id))
    
    return render_template('find.html', all_influencers=all_influencers, campaign_id=campaign_id, niches = niches,
                           current_url=current_url, uname= user_id, total_pages=total_pages,
        current_page=current_page)

@app.route("/sponsor/statistics/<user_id>", methods=["Get","POST"])
@auth_required
def statistics_sponsor(user_id):
    campaigns_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.sponsor_id == user_id).scalar() or 0
    active_campaigns_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.sponsor_id == user_id, Campaign.status.in_(['Accepted', 'Payment'])).scalar() or 0
    pending_campaigns_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.sponsor_id == user_id, Campaign.status == 'Pending').scalar() or 0
    completed_campaigns_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.sponsor_id == user_id, Campaign.status == 'Completed').scalar() or 0
    flagged_campaigns_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.sponsor_id == user_id, Campaign.status == 'Flagged').scalar() or 0

    public_campaigns_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.sponsor_id == user_id, Campaign.visibility == 'Public').scalar() or 0
    private_campaigns_no = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.sponsor_id == user_id, Campaign.visibility == 'Private').scalar() or 0

    # Total invoiced amount for a specific sponsor
    total_invoiced_amount = db.session.query(func.sum(Invoice.payment_amount)).filter(Invoice.sponsor_id == user_id).scalar() or 0

    # Total paid amount for the invoices of a specific sponsor
    total_paid_amount = db.session.query(func.sum(Payment.amount_paid)).join(Invoice, Payment.invoice_id == Invoice.id).filter(Invoice.sponsor_id == user_id).scalar() or 0
    # Count of pending invoices for the specific sponsor
    pending_invoices = db.session.query(func.count(Invoice.id)).filter(Invoice.sponsor_id == user_id, Invoice.status == 'Unpaid').scalar() or 0

        

    # Campaign data and visibility data to be passed to the template
    campaign_data = [campaigns_no, active_campaigns_no, pending_campaigns_no, completed_campaigns_no, flagged_campaigns_no]
    visibility_data = [public_campaigns_no, private_campaigns_no]

    return render_template("stat.html", uname=user_id, campaign_data=campaign_data, visibility_data=visibility_data,
                            total_invoiced_amount=total_invoiced_amount, total_paid_amount=total_paid_amount,
                            pending_invoices=pending_invoices)


@app.route("/influencer/statistics/<user_id>", methods=["GET", "POST"])
@auth_required
def statistics_influencer(user_id):
    current_url = request.url
    influencer = Influencer.query.get(user_id)
    ads_request_no = Ads_Request.query.filter_by(influencer_id=user_id).count()
    active_campaign_no = Ads_Request.query.filter_by(influencer_id=user_id, status='Accepted').count()
    complete_campaign_no = Campaign.query.filter_by(influencer_id=user_id, status='Completed').count()
    
    earnings_per_month = (
    db.session.query(
        func.extract('year', Payment.payment_date).label('year'),
        func.extract('month', Payment.payment_date).label('month'),
        func.sum(Payment.amount_paid).label('total_amount')
    )
    .join(Invoice, Invoice.id == Payment.invoice_id)
    .filter(Invoice.influencer_id == user_id)  # Filter by influencer_id via the Invoice model
    .group_by(func.extract('year', Payment.payment_date), func.extract('month', Payment.payment_date))
    .order_by(func.extract('year', Payment.payment_date), func.extract('month', Payment.payment_date))
    .all())
    if earnings_per_month:
        months = [
        datetime(year=int(record.year), month=int(record.month), day=1).strftime("%b '%y")
        for record in earnings_per_month]
        earnings = [
        float(record.total_amount) if record.total_amount else 0
        for record in earnings_per_month]
    else:
        months = []
        earnings = []
    

    ads = [str(ads_request_no), str(active_campaign_no), str(complete_campaign_no)]

    return render_template("stat.html", earnings=earnings, months=months, ads=ads, current_url=current_url, uname=user_id)

'''
@app.route("/admin/statistics", methods=["GET"])
@auth_required
def statistics_Admin():
    # Fetch total number of influencers
    user_no = User_Info.query.count()
    influencers_no = Influencer.query.count()
    # Fetch total number of sponsors
    sponsors_no = Sponsor.query.count()
    # Fetch total number of campaigns
    campaigns_no = Campaign.query.count()
    # Fetch total number of pending_campaigns
    pending_campaigns_no = Campaign.query.filter_by(status='Pending').count()
    # Fetch total number of flagged campaigns
    flagged_campaigns_no = Campaign.query.filter_by(status='Flagged').count()
    # Fetch total number of completed campaigns
    completed_campaigns_no = Campaign.query.filter_by(status='Completed').count()
    # Fetch total number of active campaigns
    active_campaigns_no = Campaign.query.filter_by(status='Accepted').count()
    # Fetch Public campaigns
    public_campaigns_no = Campaign.query.filter_by(visibility= 'Public').count()
     # Fetch Private campaigns
    private_campaigns_no = Campaign.query.filter_by(visibility= 'Private').count()

    user_data = [user_no, influencers_no, sponsors_no]
    campaign_data = [campaigns_no, active_campaigns_no, pending_campaigns_no, completed_campaigns_no, flagged_campaigns_no]
    visibility_data = [public_campaigns_no, private_campaigns_no]

    print(campaign_data)

    print(visibility_data)

    return render_template("stat.html", user_data=user_data, campaign_data=campaign_data, visibility_data=visibility_data, current_url=request.url)
'''

@app.route('/admin/statistics', methods=["GET"])
def admin_statistics():
    totaluser_no = db.session.query(User_Info).filter(User_Info.role.in_(['influencer','sponsor'])).count() or 0
    influencers_no = Influencer.query.count() or 0
    sponsors_no = Sponsor.query.count() or 0
    campaigns_no = Campaign.query.count()
    pending_campaigns_no = Campaign.query.filter_by(status='Pending').count()
    flagged_campaigns_no = Campaign.query.filter_by(status='Flagged').count()
    completed_campaigns_no = Campaign.query.filter_by(status='Completed').count()
    active_campaigns_no = db.session.query(Campaign).filter(Campaign.status.in_(['Accepted','Payment'])).count()
    public_campaigns_no = Campaign.query.filter_by(visibility= 'Public').count()
    private_campaigns_no = Campaign.query.filter_by(visibility= 'Private').count()

    user_data = [totaluser_no, influencers_no, sponsors_no]
    campaign_data = [campaigns_no, active_campaigns_no, pending_campaigns_no, completed_campaigns_no, flagged_campaigns_no]
    visibility_data = [public_campaigns_no, private_campaigns_no]
    
    total_influencers = db.session.query(func.count(Influencer.influencer_id)).scalar()
    total_sponsors = db.session.query(func.count(Sponsor.sponsor_id)).scalar()
    total_campaigns = db.session.query(func.count(Campaign.campaign_id)).scalar()
    ongoing_campaigns = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.status == 'Ongoing').scalar()
    completed_campaigns = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.status == 'Completed').scalar()
    flagged_campaigns = db.session.query(func.count(Campaign.campaign_id)).filter(Campaign.status == 'Flagged').scalar()

    total_ads_requests = db.session.query(func.count(Ads_Request.id)).scalar()
    pending_ads_requests = db.session.query(func.count(Ads_Request.id)).filter(Ads_Request.status == 'Pending').scalar()
    approved_ads_requests = db.session.query(func.count(Ads_Request.id)).filter(Ads_Request.status == 'Approved').scalar()
    rejected_ads_requests = db.session.query(func.count(Ads_Request.id)).filter(Ads_Request.status == 'Rejected').scalar()

    
    total_invoiced_amount = db.session.query(func.sum(Invoice.payment_amount)).scalar()
    total_paid_amount = db.session.query(func.sum(Payment.amount_paid)).scalar()
    pending_invoices = db.session.query(func.count(Invoice.id)).filter(Invoice.status == 'Unpaid').scalar()

    return render_template('admin_statistics1.html',
                           total_influencers=total_influencers,
                           total_sponsors=total_sponsors,
                           total_campaigns=total_campaigns,
                           ongoing_campaigns=ongoing_campaigns,
                           completed_campaigns=completed_campaigns,
                           flagged_campaigns=flagged_campaigns,
                           total_ads_requests=total_ads_requests,
                           pending_ads_requests=pending_ads_requests,
                           approved_ads_requests=approved_ads_requests,
                           rejected_ads_requests=rejected_ads_requests,
                           total_invoiced_amount=total_invoiced_amount,
                           total_paid_amount=total_paid_amount,
                           pending_invoices=pending_invoices,
                           user_data=user_data,
                           campaign_data=campaign_data,
                           visibility_data=visibility_data)

@app.route("/influencer/profile/<user_id>", methods = ["GET", "POST"])
@auth_required
def profile_influencer(user_id):
    influencers = Influencer.query.get(user_id)
    niche =Niche.query.get(influencers.niche_id)
    social_media = influencers.social_handle
    print(social_media)
    reviews_no = db.session.query(func.count(Review.id)).filter(Review.influencer_id==user_id).scalar() or 0
    recommends_no = db.session.query(func.count(Recommend.id)).filter(Recommend.influencer_id==user_id).scalar() or 0
    t_rating = db.session.query(func.sum(Rating.rating)).filter(Rating.influencer_id==user_id).scalar() or 0
    rating_no = db.session.query(func.count(Rating.id)).filter(Rating.influencer_id==user_id).scalar() or 0
    avg_rating = ((t_rating/rating_no) if rating_no != 0 else 0)

    reviews = Review.query.filter_by(influencer_id=user_id).order_by(Review.id.desc()).limit(5).all()

    return render_template("profile.html", influencers=influencers,niche=niche, social_media=social_media, recommends_no=recommends_no,
                            reviews_no=reviews_no, avg_rating=avg_rating, current_url=request.url, uname=user_id, reviews=reviews)

@app.route('/edit_profile/<user_id>', methods=['GET', 'POST'])
def edit_profile(user_id):
    userInfo = User_Info.query.get(user_id)
    print(userInfo)
    influencer = Influencer.query.get(user_id)
    niche =Niche.query.get(influencer.niche_id)

    if not userInfo:
        flash('Influencer not found!', 'error')
        return redirect(url_for('profile_influencer',user_id=user_id))  # Handle case if influencer does not exist

    if request.method == 'POST':
        # Extract data from the form
        userid = request.form.get('U_id')
        mobile_no = request.form.get('mobile')
        influencer.username = request.form.get('U_name')
        influencer.email = request.form.get('email')
        influencer.address = request.form.get('address')
        influencer.bio = request.form.get('bio')
        influencer.niche_id = request.form.get('nic')

        if len(mobile_no) != 10 or not mobile_no.isdigit():
            flash('Invalid mobile number!', 'error')
            return redirect(url_for('profile_influencer',user_id=user_id))
        influencer.mobile_no = mobile_no

        user = User_Info.query.filter_by(userid=userid).first()
       

        if user and user.userid!=influencer.influencer_id:
            flash('UserID already exists!')
            return redirect(url_for('profile_influencer',user_id=user_id))
        
        # Handle profile picture upload
        
        profile_photo = request.files.get('photo')
        if profile_photo and allowed_file(profile_photo.filename):
            filename = secure_filename(profile_photo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            profile_photo.save(filepath)
            influencer.profile_photo = f'/{filepath}'

        # Handle social media links
        social_media_platforms = ['instagram', 'facebook', 'youtube', 'linkedin']

        # Retrieve influencer ID (user_id assumed to be available in the request)
        try:
            for platform in social_media_platforms:
                link = request.form.get(platform)
                print('#############')

                print(link)
                print()
       
                print('###############')
        
                if link and link.strip():  # Ensure the link is not empty or just spaces
                    # Check if a social media link for this platform already exists for this influencer
                    social_media_entry = Social_media.query.filter_by(influencer_id=user_id, platform=platform).first()

                    if social_media_entry:
                        # Update the existing entry with the new link
                        social_media_entry.link = link
                    else:
                        # Create a new entry if none exists for this platform
                        new_social_media = Social_media(
                        influencer_id=user_id,
                            platform=platform,
                            link=link
                        )
                        db.session.add(new_social_media)
        except SQLAlchemyError as e:
            # Rollback changes in case of an error and log the exception
            db.session.rollback()
            print(f"Database error: {e}")

        print('#############')

        print()
        print()
       
        print('###############')

        db.session.commit()  # Commit changes
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile_influencer',user_id=user_id))
        
    
    return render_template('editProfile.html', influencer=influencer, niches=Niche.query.all(), uname=user_id,niche=niche)



@app.route("/sponsor/profile/<user_id>", methods=["GET", "POST"])
@auth_required
def profile_sponsor(user_id):
    sponsors = Sponsor.query.get(user_id)
    social_media = sponsors.social_handle
    return render_template("publicProfile.html", sponsors=sponsors, social_media=social_media, uname=user_id)

@app.route("/sponsor/influencer/<user_id>/profile/<influencer_id>", methods=["GET","POST"])
def influencer_public(user_id, influencer_id):
    influencers = Influencer.query.get(influencer_id)
    niche_all =Niche.query.get(influencers.niche_id)
    social_media = influencers.social_handle
    reviews_no = db.session.query(func.count(Review.id)).filter(Review.influencer_id==influencer_id).scalar() or 0
    recommends_no = db.session.query(func.count(Recommend.id)).filter(Recommend.influencer_id==influencer_id).scalar() or 0
    t_rating = db.session.query(func.sum(Rating.rating)).filter(Rating.influencer_id==influencer_id).scalar() or 0
    rating_no = db.session.query(func.count(Rating.id)).filter(Rating.influencer_id==influencer_id).scalar() or 0
    avg_rating = ((t_rating/rating_no) if rating_no != 0 else 0)

    reviews = Review.query.filter_by(influencer_id=influencer_id).order_by(Review.id.desc()).limit(5).all()

    if request.method =="POST":
        recommends = Recommend.query.filter_by(influencer_id=influencer_id, sponsor_id=user_id).first()
        if not recommends:
            recommend = Recommend(influencer_id=influencer_id, sponsor_id=user_id)
            db.session.add(recommend)
            db.session.commit()
            flash("Recommendation sent successfully!", "success")
            return redirect(url_for('influencer_public', user_id=user_id, influencer_id=influencer_id))
        else:
            recommend = Recommend.query.filter_by(influencer_id=influencer_id, sponsor_id=user_id).first()
            db.session.delete(recommend)
            db.session.commit()
            flash("Recommendation removed successfully!", "success")
            return redirect(url_for('influencer_public', user_id=user_id, influencer_id=influencer_id))


    return render_template("publicProfile.html", influencers=influencers,niche_all=niche_all, social_media=social_media, recommends_no=recommends_no,
                            reviews_no=reviews_no, avg_rating=avg_rating, current_url=request.url, uname=user_id, reviews=reviews)

@app.route("/influencer/sponsor/<user_id>/profile/<sponsor_id>", methods=["GET"])
def sponsor_public(user_id, sponsor_id):
    sponsors = Sponsor.query.get(sponsor_id)
    if sponsors.social_handle :
        social_media = sponsors.social_handle
    else:
        social_media=[]
    return render_template("publicProfile.html", sponsors=sponsors, social_media=social_media, uname=user_id, sponsor_id=sponsor_id)

@app.route('/addniche', methods=["POST"])
@auth_required
def addNiche():
    if request.method == "POST":
        niche = request.form.get('niche')

        # Retrieve all niches
        niches = [n.name for n in Niche.query.all()]
        
        if not niches or niche not in niches:
            # Add niche if it doesn't exist
            addniches = Niche(name=niche)
            db.session.add(addniches)
            db.session.commit()
            flash("Niche added successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            # If niche already exists, show a message
            flash("Niche already exists!", "danger")
            return redirect(url_for('admin_dashboard'))

@app.route("/admin/search", methods=["GET", "POST"])
@auth_required
def admin_search():
    search_query = request.form.get('search_query')
    
    if search_query:
        un_flagged_campaigns = Campaign.query.filter(
            Campaign.status != 'Flagged',
            db.or_(Campaign.campaign_id.like(f"%{search_query}%"), Campaign.campaign_name.like(f"%{search_query}%"))
        ).all()
    else:
        un_flagged_campaigns = Campaign.query.filter(Campaign.status != 'Flagged').all()

    niches = Niche.query.all()
    
    return render_template("admin_search.html", un_flagged_campaigns=un_flagged_campaigns, niches=niches)

@app.route("/admin/flag_campaign/<string:campaign_id>", methods=["POST"])
@auth_required
def flag_campaign(campaign_id):
    campaign = Campaign.query.filter_by(campaign_id=campaign_id).first()
    u1= User_Info.query.filter_by(userid=campaign.influencer_id).first()
    u2= User_Info.query.filter_by(userid=campaign.sponsor_id).first()
    if campaign:
        campaign.status = 'Flagged'
        db.session.commit()
        if not flag_id(campaign.sponsor_id):
            user1=Flagged(user_id=campaign.sponsor_id,strikes=campaign_id)
            db.session.add(user1)
            db.session.commit()
        if campaign.influencer_id and (not flag_id(campaign.influencer_id)):
            user2=Flagged(user_id=campaign.influencer_id,strikes=campaign_id)
            db.session.add(user2)
            db.session.commit()
    return redirect(url_for('admin_search'))

@app.route("/admin/unflag_campaign/<string:campaign_id>", methods=["POST","GET"])
@auth_required
def unflag_campaign(campaign_id):
    campaign = Campaign.query.filter_by(campaign_id=campaign_id).first()
    if campaign:
        campaign.status = 'Accepted'
        db.session.commit()
    flash('A campaign is available')
    return redirect(url_for('admin_dashboard'))

@app.route("/invoice/<invoice_id>", methods=["GET"])
@auth_required
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    campaign = Campaign.query.filter_by(campaign_id=invoice.campaign_id).first_or_404()
    influencer = Influencer.query.filter_by(influencer_id=invoice.influencer_id).first_or_404()
    sponsor = Sponsor.query.filter_by(sponsor_id=invoice.sponsor_id).first_or_404()

    return render_template('invoice.html', invoice=invoice, campaign=campaign, influencer=influencer, sponsor=sponsor)

@app.route('/sponsor/<user_id>/invoice/<invoice_id>/payment/gateway', methods=["GET", "POST"])
@auth_required
def payment(user_id, invoice_id):
    sponsor = Sponsor.query.filter_by(sponsor_id=user_id).first()
    unpaid_invoice = Invoice.query.filter_by(id=invoice_id, status='Unpaid').first()
    campaign = Campaign.query.get(unpaid_invoice.campaign_id)

    if not unpaid_invoice or not sponsor:
        flash('Invalid invoice or sponsor.', 'error')
        return redirect(url_for('sponsor_dashboard', user_id=user_id))

    if request.method == "POST":
        amount = request.form.get('amount')
        payment_method = request.form.get('method')

        try:
            amount = float(amount)
        except ValueError:
            flash('Invalid amount entered. Please enter a numeric value.', 'error')
            return redirect(url_for('payment', user_id=user_id, invoice_id=invoice_id))

        if amount != unpaid_invoice.payment_amount:
            flash('The amount entered does not match the invoice amount.', 'error')
            return redirect(url_for('payment', user_id=user_id, invoice_id=invoice_id))

        if not payment_method:
            flash('Payment method is required.', 'error')
            return redirect(url_for('payment', user_id=user_id, invoice_id=invoice_id))

        new_payment = Payment(invoice_id=unpaid_invoice.id,payment_date=datetime.utcnow(),amount_paid=amount,
                              method=payment_method,payment_status="Paid")
        unpaid_invoice.status = 'Paid'
        campaign.status = 'Completed'

        try:
            db.session.add(new_payment)
            db.session.commit()
            flash('Payment successful!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while processing your payment. Please try again.', 'error')
            return redirect(url_for('payment', user_id=user_id, invoice_id=invoice_id))

        return redirect(url_for('sponsor_dashboard', user_id=user_id))

    return render_template('payment.html', uname=user_id, invoice_id=invoice_id, sponsor=sponsor, invoice=unpaid_invoice)
