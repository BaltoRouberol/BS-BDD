# -*- coding: utf-8 -*-
"""
Models describing internships and their relation with students and scholar years
"""

from django.db import models

from emploi.models import Employeur
from annee.models import PromoBSEleve

class Stage(models.Model):
    """Model describing an internship"""
    
    employeur = models.ForeignKey(Employeur)
    sujet     = models.TextField(max_length=2000)
    duree     = models.PositiveSmallIntegerField(help_text=u"En mois. Mettez un chiffre rond", verbose_name=u"Durée du stage")
    salaire   = models.DecimalField(decimal_places=2, max_digits=5, help_text=u"En euros")

    def __unicode__(self):
        return '%s - %s' % (self.employeur, self.sujet)

class StageEleve(models.Model):
    """Association between an internship and the scholar year of a student"""
    
    promo_eleve = models.ForeignKey(PromoBSEleve)
    stage       = models.ForeignKey(Stage)

    def __unicode__(self):
        return '%s - %s' %(self.promo_eleve, self.stage)

    class Meta:
        verbose_name = u"Stage effectué par un élève"
        verbose_name_plural = u"Stages effectués par des élèves"
    
