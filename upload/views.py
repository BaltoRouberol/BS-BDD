# -*- coding: utf-8 -*-
"""
Views related to data input
"""

from os.path import exists
from os import makedirs
from datetime import datetime
from random import choice
import string

from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response
from django.http import Http404, HttpResponseRedirect
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from upload.forms import DataInputForm
from excel.headers import *
from excel.handlers import BSExcelFileData
from BS.settings import MEDIA_ROOT

from etat_civil.models import EtatCivil
from international.models import Pays, Universite
from admission.models import Admission, FiliereAdmission, DomaineAdmission
from annee.models import PromoBS, PromoBSEleve, ResultatEleve, EchangeEleve
from eleve.models import Eleve
from stage.models import Stage, StageEleve
from emploi.models import Employeur


def validate(request):
    """Manage the uploading of new data and storing in the Database"""
    
    if request.method == 'POST':
        form = DataInputForm(request.POST, request.FILES)
        if form.is_valid():
            # ALL THE  MAGIC HAPPENS HERE
            upload, errors = validate_data(request.FILES['file'])
            if len(errors)==0:
                return HttpResponseRedirect('success/')
            else :
                return render_to_response('upload/upload.html', RequestContext(request,{'form': form, 'errors': errors}))
    else:
        form = DataInputForm()
    return render_to_response('upload/upload.html', RequestContext(request,{'form': form}))

def save_excel(file):
    """Save the input excel file in the /static/upload/ directory"""
    # EXCEL SAVE PATH
    filepath = MEDIA_ROOT+'/upload/'
    filename = 'tmp_xl_data.xls'
    if not exists(filepath):
        makedirs(filepath)   
        
    # SAVE EXCEL FILE
    with open(filepath+filename, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    return destination

def create_etat_civil(row):
    """Read an excel row and save the corresponding EtatCivil object in database"""
    errors = []
    ec = EtatCivil()
    ec.nom_insa = row['nom_insa'].capitalize()
    ec.nom_actuel = row['nom_actuel'].capitalize()
    ec.prenom =row['prenom'].capitalize()
    ec.num_etudiant = row['num_etudiant']
    ec.sexe = row['sexe'].upper()
    ec.date_naissance = datetime(*[int(i) for i in row['date_de_naissance'].split("/")][::-1])
    try:
        ec.nationalite = Pays.objects.get(nom=unicode(row['nationalite']))
    except Pays.DoesNotExist:
        ec.nationalite = Pays(nom=unicode(row['nationalite']))
    ec.adresse_1 = row['adresse_1_(personnelle)']
    ec.zip_adresse_1 = row['code_postal_1']
    ec.adresse_2 = row['adresse_2_(parentale)']
    ec.zip_adresse_2 = row['code_postal_2']
    ec.email_1 = row['email_1']
    ec.email_2 = row['email_2']
    try:
        ec.full_clean()
    except ValidationError, e:
        m = dict(e.message_dict)
        errors.append([str("%s %s"%(ec.prenom, ec.nom_insa)), [list(k) for k in zip(m.keys(),m.values())]])
    return ec, errors 
            
def create_user(etat_civil):
    """Create user associated with an etat civil"""
    errors = []
    us = User()
    us.username = etat_civil.prenom[0].lower() + etat_civil.nom_insa.lower()
    chars = string.ascii_letters + string.digits
    us.password = "".join(choice(chars) for x in range(8)) # RANDOM PASSWORD OF 8 CHARACTERS
    try:
        us.full_clean()
    except ValidationError, e:
        m = dict(e.message_dict)
        errors.append([str("%s %s"%(etat_civil.prenom, etat_civil.nom_insa)), [list(k) for k in zip(m.keys(),m.values())]])  
    return us, errors                      
    
def create_admission(row, etat_civil):
    """Read an excel row and save the corresponding Admission object in database"""
    errors = []
    ad = Admission()
    try :
        ad.filiere_org = FiliereAdmission.objects.get(nom=row['origine_avant_BS'])
    except FiliereAdmission.DoesNotExist:
        ad.filiere_org = FiliereAdmission(nom=row['origine_avant_BS'])
    try:
        ad.domaine_org = DomaineAdmission.objects.get(nom=row['filiere_avant_BS'])
    except DomaineAdmission.DoesNotExist:
        ad.domaine_org = DomaineAdmission(nom=row['filiere_avant_BS'])
    ad.annee_admission = row['annee_admission']
    ad.rang_pre_BS = row['classement_avant_BS']
    ad.taille_promo_pre_BS = row['taille_de_promo_avant_BS']
    try:
        ad.full_clean()
    except ValidationError, e:
        m = dict(e.message_dict)
        errors.append([str("%s %s"%(etat_civil.prenom, etat_civil.nom_insa)), [list(k) for k in zip(m.keys(),m.values())]]) 
    return ad, errors                      
    
def create_promo_bs(row, etat_civil, year):
    """Read an excel row and save the corresponding PromoBS object in database
    corresponding to the 3rd year"""
    errors = []
    try:
        pbs = PromoBS.objects.get(
            niveau = year,
            filiere = row['filiere_BS'],
            categorie = row['scolarite_%de_annee'%(year)],
            num_promo = row['promo_BS'],
            taille_promo = row['taille_promo_%de_annee'%(year)],
            annee = row['annee_%de_annee'%(year)])
    except PromoBS.DoesNotExist:
        pbs = PromoBS(
            niveau = year,
            filiere = row['filiere_BS'],
            categorie = row['scolarite_%de_annee'%(year)],
            num_promo = row['promo_BS'],
            taille_promo = row['taille_promo_%de_annee'%(year)],
            annee = row['annee_%de_annee'%(year)])
    try:
        pbs.full_clean()
    except ValidationError, e:
        m = dict(e.message_dict)
        errors.append([str("%s %s"%(etat_civil.prenom, etat_civil.nom_insa)), [list(k) for k in zip(m.keys(),m.values())]]) 
    return pbs, errors                      
    
def create_resultat_eleve(row, etat_civil, annee_eleve):
    """ Reads an excel row and create the corresponding academic results object"""
    errors = []
    res = ResultatEleve()
    res.promo_eleve = annee_eleve
    res.rang = row['classement_%se_annee'%(annee_eleve.promo_bs.niveau)]
    try:
        res.full_clean()
    except ValidationError, e:
        m = dict(e.message_dict)
        errors.append([str("%s %s"%(etat_civil.prenom, etat_civil.nom_insa)), [list(k) for k in zip(m.keys(),m.values())]]) 
    return res, errors 

def create_echange_eleve(row, etat_civil, annee_eleve):
    """Reads an excel row and create the corresponding academic exchange object, if need be"""
    if row['pays_echange_%se_annee'%(annee_eleve.promo_bs.niveau)] != '': # If excel sheet contains info
        errors = []
        ech = EchangeEleve()
        ech.promo_eleve = annee_eleve
        try:
            pays = Pays.objects.get(nom = row['pays_echange_%se_annee'%(annee_eleve.promo_bs.niveau)])
        except Pays.DoesNotExist:
            pays = Pays(nom = row['pays_echange_%se_annee'%(annee_eleve.promo_bs.niveau)])
            
        try:  
            ech.universite = Universite.objects.get(nom=row['universite_echange_%se_annee'%(annee_eleve.promo_bs.niveau)],
                                                    pays = pays)
        except Universite.DoesNotExist:
            ech.universite = Universite(nom=row['universite_echange_%se_annee'%(annee_eleve.promo_bs.niveau)],
                                        pays = pays)
        ech.duree = row['duree_echange_%se_annee'%(annee_eleve.promo_bs.niveau)]
        try:
            ech.full_clean()
        except ValidationError, e:
            m = dict(e.message_dict)
            errors.append([str("%s %s"%(etat_civil.prenom, etat_civil.nom_insa)), [list(k) for k in zip(m.keys(),m.values())]]) 
        return ech, errors
    else:
        return None, []


def create_stage_eleve(row, etat_civil, annee_eleve):
    """Reads an excel row and create the corresponding Stage and StageEleve objects if need be"""
    if row['employeur_stage_%se_annee'%(annee_eleve.promo_bs.niveau)] != '': # If excel sheet contains info
        errors = []
        st_el = StageEleve()
        st_el.promo_eleve = annee_eleve
        try:
            emp = Employeur.objects.get(nom=row['employeur_stage_%se_annee'%(annee_eleve.promo_bs.niveau)])
        except Employeur.DoesNotExist:
            emp = Employeur(nom=row['employeur_stage_%se_annee'%(annee_eleve.promo_bs.niveau)])
        try:
            st_el.stage = Stage.objects.get(
                employeur = emp,
                sujet = row['sujet_stage_%se_annee'%(annee_eleve.promo_bs.niveau)],
                duree = row['duree_stage_%se_annee'%(annee_eleve.promo_bs.niveau)],
                salaire = str(row['salaire_stage_%se_annee'%(annee_eleve.promo_bs.niveau)]))               
        except Stage.DoesNotExist:
            st_el.stage = Stage(
                employeur = emp,
                sujet = row['sujet_stage_%se_annee'%(annee_eleve.promo_bs.niveau)],
                duree = row['duree_stage_%se_annee'%(annee_eleve.promo_bs.niveau)],
                salaire = str(row['salaire_stage_%se_annee'%(annee_eleve.promo_bs.niveau)]))
        try:
            st_el.full_clean()
        except ValidationError, e:
            m = dict(e.message_dict)
            errors.append([str("%s %s"%(etat_civil.prenom, etat_civil.nom_insa)), [list(k) for k in zip(m.keys(),m.values())]]) 
        return st_el, errors
    else:
        return None, []
    
def validate_data(file):
    """
    Save the input excel file in the /MEDIA_ROOT/upload/ directory,
    instanciate database-compliant objects and populate database

    At each step of the process, we run the model 'full_clean()' method.
    We append potential creation errors in a list call 'errors'. 
    At the end, if 'errors' is empty, we initiate the DB populating.
    
    """
    xl = BSExcelFileData(save_excel(file).name)
    sheet = 0
    rowmax = xl.get_corners(sheet)[-1]
    errors = []
    upload = True # If upload still True at the end, --> save

    for nrow in range (1, rowmax+1): 
        row = xl.get_row(sheet, nrow)

        # - ETAT CIVIL
        ec, e = create_etat_civil(row)
        if len(e) > 0:errors.append(e)

        # - USER
        us, e = create_user(ec)    
        if len(e) > 0:errors.append(e)
        
        # - ADMISSION
        ad, e = create_admission(row, ec)
        if len(e) > 0:errors.append(e)

        # - ELEVE
        el = Eleve(user=us, etat_civil=ec, admission=ad)
        
        # - 3e ANNEE
        # -- PROMO_BS
        third, e = create_promo_bs(row, ec, 3)
        if len(e) > 0:errors.append(e)
        #  print third
        # -- PROMO_BS <-> ELEVE
        eleve_third = PromoBSEleve(eleve=el, promo_bs=third)
        # print eleve_third
        # -- PROMO_BS <-> ELEVE <-> RESULTAT
        resultat_eleve_third, e = create_resultat_eleve(row, ec, eleve_third)
        print resultat_eleve_third
        if len(e) > 0:errors.append(e)
        # -- PROMO_BS <-> ELEVE <-> ECHANGE
        echange_eleve_third, e = create_echange_eleve(row, ec, eleve_third)
        print echange_eleve_third
        if len(e) > 0:errors.append(e)
        # -- PROMO_BS <-> ELEVE <-> STAGE
        stage_eleve_third, e = create_stage_eleve(row, ec, eleve_third)
        print stage_eleve_third
        if len(e) > 0:errors.append(e)

        # - 4e ANNEE
        if row['scolarite_4e_annee'] != '':
            # -- PROMO_BS
            fourth, e = create_promo_bs(row, ec, 4)
            if len(e) > 0:errors.append(e)
            print fourth
            # -- PROMO_BS <-> ELEVE
            eleve_fourth = PromoBSEleve(eleve=el, promo_bs=fourth)
            print eleve_fourth
            # -- PROMO_BS <-> ELEVE <-> RESULTAT
            resultat_eleve_fourth, e = create_resultat_eleve(row, ec, eleve_fourth)
            print resultat_eleve_fourth
            if len(e) > 0:errors.append(e)
            # -- PROMO_BS <-> ELEVE <-> ECHANGE
            echange_eleve_fourth, e = create_echange_eleve(row, ec, eleve_fourth)
            print echange_eleve_fourth
            if len(e) > 0:errors.append(e)
            # -- PROMO_BS <-> ELEVE <-> STAGE
            stage_eleve_fourth, e = create_stage_eleve(row, ec, eleve_fourth)
            print stage_eleve_fourth
            if len(e) > 0:errors.append(e)

        # - 5e ANNEE
        if row['scolarite_5e_annee'] != '':
            # -- PROMO_BS
            fifth, e = create_promo_bs(row, ec, 5)
            if len(e) > 0:errors.append(e)
            print fifth
            # -- PROMO_BS <-> ELEVE
            eleve_fifth = PromoBSEleve(eleve=el, promo_bs=fifth)
            print eleve_fifth
            # -- PROMO_BS <-> ELEVE <-> STAGE
            stage_eleve_fifth, e = create_stage_eleve(row, ec, eleve_fifth)
            if len(e) > 0:errors.append(e)

        
    if len(errors)==0:
        upload = False
    else:
        upload = True
    return (upload, errors)


    
    
    

