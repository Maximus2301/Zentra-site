import React from 'react';
import { DOCTOR_CONFIG } from '../config/doctorConfig';
import { MessageSquare, Calendar, ShieldCheck, MapPin, CheckCircle2, Heart } from 'lucide-react';

export const Hero: React.FC = () => {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-navy-50/60 via-white to-slate-50 py-16 md:py-24 border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          
          {/* Left Column: Clinical Authority Copy (60%) */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Top Clinical Badge */}
            <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-teal-50 border border-teal-200/80 text-teal-700 text-xs font-bold tracking-wider uppercase">
              <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse"></span>
              <span>{DOCTOR_CONFIG.hero.badge}</span>
            </div>

            {/* H1 Doctor Name */}
            <div className="space-y-2">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-navy-900 tracking-tight leading-tight">
                {DOCTOR_CONFIG.hero.headline}
              </h1>
              <p className="text-lg sm:text-xl font-semibold text-teal-700">
                {DOCTOR_CONFIG.identity.specialty} • {DOCTOR_CONFIG.identity.superSpecialtySummary}
              </p>
            </div>

            {/* Mandatory NMC Credentials Line */}
            <div className="inline-block p-3 rounded-lg bg-slate-100/90 border border-slate-200 text-xs sm:text-sm font-medium text-slate-700">
              <span className="font-bold text-navy-800">Qualifications & Registration:</span>{' '}
              <span>{DOCTOR_CONFIG.identity.degreeNote}</span> •{' '}
              <span className="text-navy-900 font-semibold">{DOCTOR_CONFIG.identity.registrationNumber}</span>
            </div>

            {/* Sub-headline */}
            <p className="text-lg sm:text-xl text-slate-750 leading-relaxed max-w-2xl font-normal">
              {DOCTOR_CONFIG.hero.subheadline}
            </p>

            {/* Core Trust Pillars Strip */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-700 bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs">
                <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
                <span>Unhurried Consultations</span>
              </div>
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-700 bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs">
                <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
                <span>Bilingual: Hindi & English</span>
              </div>
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-700 bg-white p-2.5 rounded-lg border border-slate-200/80 shadow-xs">
                <ShieldCheck className="w-4 h-4 text-teal-600 shrink-0" />
                <span>NMC Ethical Compliance</span>
              </div>
            </div>

            {/* CTA Action Buttons */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center space-y-3 sm:space-y-0 sm:space-x-4 pt-4">
              <a
                href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-7 py-3.5 rounded-xl text-base font-bold text-white bg-teal-600 hover:bg-teal-700 active:bg-teal-800 shadow-md hover:shadow-lg transition-all space-x-2.5"
              >
                <MessageSquare className="w-5 h-5" />
                <span>{DOCTOR_CONFIG.hero.primaryButtonText}</span>
              </a>

              <a
                href="#consultation-schedule"
                className="inline-flex items-center justify-center px-6 py-3.5 rounded-xl text-base font-semibold text-navy-800 bg-white hover:bg-slate-50 border border-slate-300 shadow-xs hover:border-slate-400 transition-all space-x-2"
              >
                <Calendar className="w-5 h-5 text-slate-600" />
                <span>{DOCTOR_CONFIG.hero.secondaryButtonText}</span>
              </a>
            </div>

          </div>

          {/* Right Column: High-Trust Portrait Card & Clinical Motif (40%) */}
          <div className="lg:col-span-5 flex justify-center lg:justify-end">
            <div className="relative w-full max-w-md">
              
              {/* Subtle Decorative Background Glow */}
              <div className="absolute -inset-1.5 bg-gradient-to-r from-teal-500/20 to-navy-800/20 rounded-3xl blur-xl opacity-75"></div>

              {/* Main Card */}
              <div className="relative bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden">
                
                {/* Header Strip */}
                <div className="bg-navy-800 px-6 py-4 text-white flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Heart className="w-4 h-4 text-teal-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-teal-300">Evidence-Based Eye Care</span>
                  </div>
                  <span className="text-xs bg-navy-700 px-2.5 py-1 rounded text-slate-200 font-medium">Indore, MP</span>
                </div>

                {/* Portrait Representation / Clinical Identity */}
                <div className="p-6 sm:p-8 text-center space-y-6">
                  
                  {/* Stylized Doctor Medical Avatar / Geometric Emblem */}
                  <div className="mx-auto w-32 h-32 rounded-full bg-gradient-to-tr from-navy-800 via-navy-700 to-teal-600 p-1 shadow-lg">
                    <div className="w-full h-full rounded-full bg-white flex flex-col items-center justify-center text-navy-800">
                      <span className="text-4xl">👩‍⚕️</span>
                      <span className="text-[10px] font-bold text-teal-700 tracking-wider uppercase mt-1">Eye Specialist</span>
                    </div>
                  </div>

                  {/* Title & Practice Information */}
                  <div className="space-y-1">
                    <h3 className="text-xl font-bold text-navy-900">
                      Dr. Himani J Bharti
                    </h3>
                    <p className="text-xs font-semibold text-slate-600">
                      Ophthalmologist • Comprehensive Care
                    </p>
                    <p className="text-xs text-slate-500">
                      Indore, Madhya Pradesh
                    </p>
                  </div>

                  {/* Practice Quick Card */}
                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-200/90 text-left space-y-2.5 text-xs">
                    <div className="flex items-start space-x-2.5">
                      <MapPin className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                      <div>
                        <div className="font-bold text-slate-800">Consultation Location:</div>
                        <div className="text-slate-600">[Host Clinic Name, Indore] • Scheme 140 / Vijay Nagar</div>
                      </div>
                    </div>
                    <div className="flex items-start space-x-2.5 pt-1 border-t border-slate-200/60">
                      <Calendar className="w-4 h-4 text-teal-600 shrink-0 mt-0.5" />
                      <div>
                        <div className="font-bold text-slate-800">Visiting OPD Schedule:</div>
                        <div className="text-slate-600">Mon – Sat | 10:30 AM – 2:00 PM & 5:30 PM – 8:00 PM</div>
                      </div>
                    </div>
                  </div>

                  {/* WhatsApp Quick Link */}
                  <a
                    href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-3 px-4 rounded-xl text-xs font-bold text-teal-700 bg-teal-50 hover:bg-teal-100 border border-teal-200 transition-colors flex items-center justify-center space-x-2"
                  >
                    <MessageSquare className="w-4 h-4" />
                    <span>Inquire via WhatsApp Desk</span>
                  </a>

                </div>

                {/* Footer Assurance Banner */}
                <div className="bg-slate-50/80 px-6 py-2.5 border-t border-slate-200 text-center text-[11px] text-slate-500">
                  Prior appointment recommended for comprehensive dilated exams.
                </div>

              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};
