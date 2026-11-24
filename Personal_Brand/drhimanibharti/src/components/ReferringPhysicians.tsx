import React from 'react';
import { DOCTOR_CONFIG } from '../config/doctorConfig';
import { Stethoscope, MessageSquare, Mail, CheckCircle2 } from 'lucide-react';

export const ReferringPhysicians: React.FC = () => {
  const { referringPhysicians } = DOCTOR_CONFIG;

  return (
    <section id="referring-physicians" className="py-16 bg-navy-900 text-white relative overflow-hidden">
      
      {/* Decorative Background Elements */}
      <div className="absolute top-0 right-0 -mt-10 -mr-10 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-64 h-64 bg-navy-700/30 rounded-full blur-3xl pointer-events-none"></div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          
          {/* Left: Copy & Value Proposition (8 cols) */}
          <div className="lg:col-span-8 space-y-4">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-navy-800 border border-navy-700 text-teal-400 text-xs font-bold uppercase tracking-wider">
              <Stethoscope className="w-3.5 h-3.5" />
              <span>Physician & Optometrist Liaison</span>
            </div>

            <h3 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              {referringPhysicians.heading}
            </h3>

            <p className="text-slate-300 text-sm sm:text-base leading-relaxed max-w-2xl">
              {referringPhysicians.description}
            </p>

            {/* Checklist of Peer Services */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
              {referringPhysicians.benefits.map((b, idx) => (
                <div key={idx} className="flex items-start space-x-2 bg-navy-800/80 p-3 rounded-xl border border-navy-700">
                  <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
                  <span className="text-slate-200">{b}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Peer Action Buttons (4 cols) */}
          <div className="lg:col-span-4 flex flex-col space-y-3 justify-center">
            
            <a
              href={`https://wa.me/${DOCTOR_CONFIG.communication.whatsappDeskNumber}?text=${encodeURIComponent("Hello Dr. Himani Bharti's desk, I am a referring doctor/optometrist inquiring about clinical patient co-management.")}`}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full inline-flex items-center justify-center px-5 py-3.5 rounded-xl text-xs font-bold text-white bg-teal-600 hover:bg-teal-500 transition-all shadow-md space-x-2"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Connect via WhatsApp Desk</span>
            </a>

            <a
              href={`mailto:${DOCTOR_CONFIG.communication.peerLiaisonEmail}?subject=Clinical%20Co-Management%20Inquiry%20-%20Dr.%20Himani%20J%20Bharti`}
              className="w-full inline-flex items-center justify-center px-5 py-3 rounded-xl text-xs font-semibold text-slate-200 bg-navy-800 hover:bg-navy-750 border border-navy-700 transition-all space-x-2"
            >
              <Mail className="w-4 h-4 text-slate-400" />
              <span>{referringPhysicians.emailButtonText}</span>
            </a>

            <p className="text-[11px] text-slate-400 text-center italic">
              Structured fundus reports sent back to referring clinic within 24 hours.
            </p>

          </div>

        </div>
      </div>
    </section>
  );
};
