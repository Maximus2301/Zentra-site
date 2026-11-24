import React from 'react';
import { DOCTOR_CONFIG, ClinicLocation } from '../config/doctorConfig';
import { MapPin, Clock, Phone, MessageSquare, ExternalLink, Calendar, Info, Building2 } from 'lucide-react';

export const ConsultationSchedule: React.FC = () => {
  return (
    <section id="consultation-schedule" className="py-20 bg-slate-50 border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider">
            <Calendar className="w-3.5 h-3.5 text-teal-600" />
            <span>Practice Timings & OPD Schedule</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-navy-900 tracking-tight">
            Where to Consult in Indore
          </h2>
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed">
            Dr. Himani J Bharti conducts outpatient consultations and diagnostic evaluations across accessible medical centers in Indore. Prior appointments help minimize waiting time.
          </p>
        </div>

        {/* Dynamic Location Cards */}
        <div className="mt-14 grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {DOCTOR_CONFIG.practiceLocations.map((loc: ClinicLocation) => (
            <div
              key={loc.id}
              className={`relative rounded-3xl p-8 border transition-all duration-300 flex flex-col justify-between ${
                loc.isPrimary
                  ? 'bg-white border-teal-500/40 shadow-xl ring-1 ring-teal-500/20'
                  : 'bg-white/80 border-slate-200 shadow-md hover:shadow-lg'
              }`}
            >
              <div>
                
                {/* Status Badge & Locality */}
                <div className="flex items-center justify-between gap-4">
                  <span
                    className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-extrabold tracking-wider uppercase ${
                      loc.isPrimary
                        ? 'bg-teal-50 text-teal-700 border border-teal-200'
                        : 'bg-navy-50 text-navy-800 border border-navy-200'
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full ${loc.isPrimary ? 'bg-teal-500' : 'bg-navy-600'}`}></span>
                    <span>{loc.statusBadge}</span>
                  </span>

                  <span className="text-xs font-bold text-slate-500 flex items-center space-x-1">
                    <Building2 className="w-3.5 h-3.5 text-slate-400" />
                    <span>{loc.locality}</span>
                  </span>
                </div>

                {/* Clinic / Practice Name */}
                <h3 className="mt-5 text-2xl font-extrabold text-navy-900">
                  {loc.name}
                </h3>
                {loc.tagline && (
                  <p className="text-xs font-semibold text-teal-700 mt-1">
                    {loc.tagline}
                  </p>
                )}

                {/* Address Box */}
                <div className="mt-6 flex items-start space-x-3 text-sm text-slate-650">
                  <MapPin className="w-5 h-5 text-teal-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold text-navy-900">{loc.locality}, {loc.city}</div>
                    <div className="text-slate-600 text-xs sm:text-sm mt-0.5 leading-relaxed">{loc.fullAddress}</div>
                    {loc.landmark && (
                      <div className="text-xs text-slate-500 mt-1 italic">Landmark: {loc.landmark}</div>
                    )}
                  </div>
                </div>

                {/* Timings Box */}
                <div className="mt-6 p-4 rounded-2xl bg-slate-50 border border-slate-200/90 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-navy-900">
                    <Clock className="w-4 h-4 text-teal-600" />
                    <span>OPD Consultation Schedule</span>
                  </div>
                  <div className="text-sm font-bold text-navy-900 pl-6">
                    {loc.timings.fullTimingString}
                  </div>
                  {loc.timings.morningSlot && loc.timings.eveningSlot && (
                    <div className="grid grid-cols-2 gap-2 pl-6 pt-1 text-xs text-slate-600">
                      <div><span className="font-semibold text-slate-800">Morning:</span> {loc.timings.morningSlot}</div>
                      <div><span className="font-semibold text-slate-800">Evening:</span> {loc.timings.eveningSlot}</div>
                    </div>
                  )}
                </div>

                {/* Clinic Note if present */}
                {loc.note && (
                  <p className="mt-4 text-xs text-slate-500 flex items-start space-x-1.5 italic">
                    <Info className="w-3.5 h-3.5 text-teal-600 shrink-0 mt-0.5" />
                    <span>{loc.note}</span>
                  </p>
                )}

              </div>

              {/* Action Buttons Strip */}
              <div className="mt-8 pt-6 border-t border-slate-200/80 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  
                  {/* WhatsApp Desk CTA */}
                  <a
                    href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center px-4 py-3 rounded-xl text-xs font-bold text-white bg-teal-600 hover:bg-teal-700 transition-all shadow-sm space-x-2"
                  >
                    <MessageSquare className="w-4 h-4" />
                    <span>Book via WhatsApp Desk</span>
                  </a>

                  {/* Call Desk CTA */}
                  <a
                    href={`tel:${loc.phoneDesk}`}
                    className="inline-flex items-center justify-center px-4 py-3 rounded-xl text-xs font-bold text-navy-800 bg-slate-100 hover:bg-slate-200 transition-all border border-slate-300 space-x-2"
                  >
                    <Phone className="w-4 h-4 text-slate-600" />
                    <span>Call Appointment Desk</span>
                  </a>

                </div>

                {/* Google Maps Link */}
                <a
                  href={loc.googleMapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-700 hover:text-navy-900 hover:bg-slate-100 transition-all space-x-1.5 border border-dashed border-slate-300"
                >
                  <MapPin className="w-3.5 h-3.5 text-teal-600" />
                  <span>Open in Google Maps & View Directions</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </a>

              </div>

            </div>
          ))}
        </div>

        {/* Post Consultation Note */}
        <div className="mt-10 p-5 rounded-2xl bg-teal-50/70 border border-teal-200/80 flex items-start space-x-3 text-xs sm:text-sm text-teal-900">
          <Info className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-bold">Post-Consultation Support: </span>
            For post-consultation care sheets, report follow-ups, or inquiries regarding previous diagnostic biometry, message our dedicated{' '}
            <a
              href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="font-bold underline text-teal-800 hover:text-teal-900"
            >
              WhatsApp Care Desk
            </a>.
          </div>
        </div>

      </div>
    </section>
  );
};
