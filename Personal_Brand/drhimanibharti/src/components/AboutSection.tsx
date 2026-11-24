import React from 'react';
import { DOCTOR_CONFIG } from '../config/doctorConfig';
import { Award, GraduationCap, FileCheck, CheckCircle2 } from 'lucide-react';

export const AboutSection: React.FC = () => {
  return (
    <section id="about" className="py-20 bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-navy-50 text-navy-800 text-xs font-bold uppercase tracking-wider">
            <Award className="w-3.5 h-3.5 text-teal-600" />
            <span>Academic & Clinical Background</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-navy-900 tracking-tight">
            {DOCTOR_CONFIG.about.headline}
          </h2>
          <p className="text-base sm:text-lg font-semibold text-teal-700">
            {DOCTOR_CONFIG.about.subheadline}
          </p>
        </div>

        {/* 2-Column Bio & Credentials */}
        <div className="mt-12 grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          
          {/* Left Column: Narrative Bio & Philosophy (7 cols) */}
          <div className="lg:col-span-7 space-y-6 text-slate-700 text-base leading-relaxed">
            {DOCTOR_CONFIG.about.bioParagraphs.map((paragraph, idx) => (
              <p key={idx}>
                {paragraph}
              </p>
            ))}

            {/* Clinical Philosophy Triad */}
            <div className="mt-8 pt-6 border-t border-slate-200">
              <h4 className="text-sm font-bold uppercase tracking-wider text-navy-900 mb-4">
                Core Consultation Values:
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {DOCTOR_CONFIG.about.clinicalPhilosophy.map((item, idx) => (
                  <div key={idx} className="bg-slate-50 p-4 rounded-xl border border-slate-200/80 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-xs font-bold text-teal-700">
                      <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
                      <span>{item.title}</span>
                    </div>
                    <p className="text-xs text-slate-600 leading-normal">
                      {item.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Right Column: Structured Credentials Block (5 cols) */}
          <div className="lg:col-span-5 bg-gradient-to-br from-navy-900 to-navy-800 rounded-3xl p-7 sm:p-8 text-white shadow-xl space-y-6">
            
            <div className="flex items-center space-x-3 pb-4 border-b border-navy-700">
              <div className="w-12 h-12 rounded-xl bg-teal-500/20 border border-teal-400/30 flex items-center justify-center text-teal-300">
                <GraduationCap className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Verified Qualifications</h3>
                <p className="text-xs text-teal-300">Medical Council Credentialing</p>
              </div>
            </div>

            {/* List of Credentials */}
            <div className="space-y-4 text-xs sm:text-sm">
              {DOCTOR_CONFIG.about.credentials.map((cred, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider flex items-center space-x-1.5">
                    <FileCheck className="w-3.5 h-3.5 text-teal-400" />
                    <span>{cred.label}</span>
                  </div>
                  <div className="text-white font-medium pl-5">
                    {cred.value}
                  </div>
                </div>
              ))}
            </div>

            {/* NMC Compliance Tag */}
            <div className="mt-6 pt-4 border-t border-navy-700/80 text-[11px] text-slate-300 italic leading-relaxed">
              Dr. Himani J Bharti is registered with the State Medical Council / National Medical Commission (NMC). All practice disclosures strictly abide by Indian Medical Council professional guidelines.
            </div>

          </div>

        </div>

      </div>
    </section>
  );
};
