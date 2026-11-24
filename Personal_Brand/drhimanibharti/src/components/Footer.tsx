import React from 'react';
import { DOCTOR_CONFIG } from '../config/doctorConfig';
import { Eye, MapPin, Phone, Mail, ShieldAlert } from 'lucide-react';

export const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-slate-900 text-slate-300 border-t border-slate-800">
      
      {/* Top Footer Strip: Credentialing & Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-10">
          
          {/* Col 1: Identity & Credentials (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-navy-800 border border-teal-500/40 text-teal-400 flex items-center justify-center">
                <Eye className="w-5 h-5 text-teal-400" />
              </div>
              <div>
                <h4 className="text-xl font-bold text-white tracking-tight">
                  {DOCTOR_CONFIG.identity.fullName}
                </h4>
                <p className="text-xs font-semibold text-teal-400">
                  {DOCTOR_CONFIG.identity.specialty} • Indore, MP
                </p>
              </div>
            </div>

            {/* Mandatory Regulatory Box */}
            <div className="bg-slate-850 p-4 rounded-xl border border-slate-800 text-xs space-y-1.5 text-slate-300">
              <div className="font-bold text-white">Qualifications & Medical Council:</div>
              <div>Degrees: {DOCTOR_CONFIG.identity.degreeNote}</div>
              <div>Registration: <span className="text-teal-400 font-semibold">{DOCTOR_CONFIG.identity.registrationNumber}</span></div>
              <div className="text-slate-400 text-[11px] pt-1">
                Registered Medical Practitioner under Madhya Pradesh Medical Council / National Medical Commission (NMC).
              </div>
            </div>

            {/* Social / Directory Badges */}
            <div className="flex items-center space-x-3 pt-2">
              <a
                href={DOCTOR_CONFIG.socials.youtubeChannel}
                target="_blank"
                rel="noopener noreferrer"
                className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-red-600 text-slate-300 hover:text-white flex items-center justify-center transition-colors"
                title="YouTube Educational Channel"
                aria-label="YouTube Channel"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.5 12 3.5 12 3.5s-7.505 0-9.377.55a3.016 3.016 0 0 0-2.122 2.136C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.55 9.376.55 9.376.55s7.505 0 9.377-.55a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                </svg>
              </a>
              <a
                href={DOCTOR_CONFIG.socials.instagramProfile}
                target="_blank"
                rel="noopener noreferrer"
                className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-pink-600 text-slate-300 hover:text-white flex items-center justify-center transition-colors"
                title="Instagram Profile"
                aria-label="Instagram Profile"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
                </svg>
              </a>
              <a
                href={DOCTOR_CONFIG.socials.linkedinProfile}
                target="_blank"
                rel="noopener noreferrer"
                className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-blue-600 text-slate-300 hover:text-white flex items-center justify-center transition-colors"
                title="LinkedIn Profile"
                aria-label="LinkedIn Profile"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                </svg>
              </a>
              <a
                href={DOCTOR_CONFIG.socials.googleBusinessProfile}
                target="_blank"
                rel="noopener noreferrer"
                className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-teal-600 text-slate-300 hover:text-white flex items-center justify-center transition-colors"
                title="Google Business Profile & Reviews"
                aria-label="Google Business Profile"
              >
                <MapPin className="w-4 h-4" />
              </a>
            </div>

          </div>

          {/* Col 2: Quick Links (3 cols) */}
          <div className="lg:col-span-3 space-y-3">
            <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Clinical Navigation
            </h5>
            <ul className="space-y-2 text-xs">
              <li>
                <a href="#clinical-focus" className="hover:text-teal-400 transition-colors">
                  Areas of Clinical Focus
                </a>
              </li>
              <li>
                <a href="#consultation-schedule" className="hover:text-teal-400 transition-colors">
                  Where to Consult (OPD Schedule)
                </a>
              </li>
              <li>
                <a href="#about" className="hover:text-teal-400 transition-colors">
                  About Dr. Himani J Bharti
                </a>
              </li>
              <li>
                <a href="#patient-education" className="hover:text-teal-400 transition-colors">
                  Patient FAQs (English & Hinglish)
                </a>
              </li>
              <li>
                <a href="#referring-physicians" className="hover:text-teal-400 transition-colors">
                  Referring Physicians Liaison
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Contact & Desk Inquiries (4 cols) */}
          <div className="lg:col-span-4 space-y-3">
            <h5 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Appointment & Inquiries Desk
            </h5>
            <div className="space-y-2.5 text-xs">
              <div className="flex items-start space-x-2">
                <MapPin className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
                <span>Indore, Madhya Pradesh, India</span>
              </div>
              <div className="flex items-center space-x-2">
                <Phone className="w-4 h-4 text-teal-400 shrink-0" />
                <a href={`tel:${DOCTOR_CONFIG.communication.primaryPhone}`} className="hover:text-teal-400">
                  {DOCTOR_CONFIG.communication.primaryPhoneDisplay}
                </a>
              </div>
              <div className="flex items-center space-x-2">
                <Mail className="w-4 h-4 text-teal-400 shrink-0" />
                <a href={`mailto:${DOCTOR_CONFIG.communication.officialEmail}`} className="hover:text-teal-400">
                  {DOCTOR_CONFIG.communication.officialEmail}
                </a>
              </div>
            </div>

            <div className="pt-2">
              <a
                href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-bold bg-teal-600 hover:bg-teal-500 text-white transition-all shadow-sm"
              >
                <span>WhatsApp Appointment Desk</span>
              </a>
            </div>
          </div>

        </div>

        {/* Mandatory Medical Disclaimer & NMC Notice */}
        <div className="mt-12 pt-8 border-t border-slate-800 space-y-4">
          <div className="bg-slate-850 p-4 rounded-xl border border-slate-800 flex items-start space-x-3 text-xs text-slate-400 leading-relaxed">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-slate-300">Mandatory Medical Disclaimer: </span>
              {DOCTOR_CONFIG.footer.disclaimer}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-4 pt-2">
            <div>
              © {currentYear} Dr. Himani J Bharti. All rights reserved.
            </div>
            <div className="text-[11px] text-slate-500 text-center sm:text-right">
              {DOCTOR_CONFIG.footer.regulatoryNote}
            </div>
          </div>
        </div>

      </div>

    </footer>
  );
};
