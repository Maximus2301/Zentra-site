import React, { useState } from 'react';
import { DOCTOR_CONFIG, ClinicalFocusArea } from '../config/doctorConfig';
import { Eye, HeartPulse, ShieldCheck, Users, Sparkles, Stethoscope, ChevronRight, Check } from 'lucide-react';

export const ClinicalFocus: React.FC = () => {
  const [activeArea, setActiveArea] = useState<string | null>(null);

  // Map icon names to Lucide icon components
  const renderIcon = (name: string) => {
    const iconClass = "w-6 h-6 text-teal-600";
    switch (name) {
      case 'Eye':
        return <Eye className={iconClass} />;
      case 'HeartPulse':
        return <HeartPulse className={iconClass} />;
      case 'ShieldCheck':
        return <ShieldCheck className={iconClass} />;
      case 'Users':
        return <Users className={iconClass} />;
      case 'Sparkles':
        return <Sparkles className={iconClass} />;
      case 'Stethoscope':
      default:
        return <Stethoscope className={iconClass} />;
    }
  };

  return (
    <section id="clinical-focus" className="py-20 bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-navy-50 text-navy-800 text-xs font-bold uppercase tracking-wider">
            <span>Specialized Eye Care</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-navy-900 tracking-tight">
            Areas of Clinical Focus
          </h2>
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed">
            Comprehensive diagnostic and medical-surgical ophthalmology tailored to each stage of life, adhering strictly to evidence-based clinical protocols.
          </p>
        </div>

        {/* 6 Clean Clinical Cards */}
        <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {DOCTOR_CONFIG.clinicalFocusAreas.map((area: ClinicalFocusArea) => {
            const isExpanded = activeArea === area.id;
            return (
              <div
                key={area.id}
                className="group relative bg-slate-50/70 hover:bg-white rounded-2xl p-7 border border-slate-200 hover:border-teal-500/50 shadow-xs hover:shadow-lg transition-all duration-300 flex flex-col justify-between"
              >
                <div>
                  {/* Icon & Badge */}
                  <div className="w-13 h-13 rounded-xl bg-teal-50 border border-teal-100 flex items-center justify-center p-3 group-hover:bg-teal-600 group-hover:text-white transition-colors">
                    <span className="group-hover:brightness-200 transition-all">
                      {renderIcon(area.iconName)}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="mt-5 text-xl font-bold text-navy-900 group-hover:text-teal-700 transition-colors">
                    {area.title}
                  </h3>

                  {/* Summary */}
                  <p className="mt-3 text-sm text-slate-650 leading-relaxed">
                    {area.shortSummary}
                  </p>

                  {/* Key Clinical Insight Pill */}
                  <div className="mt-4 p-3 rounded-lg bg-white border border-slate-200/90 text-xs text-navy-850 font-medium">
                    <span className="font-bold text-teal-700">Clinical Focus: </span>
                    {area.keyInsight}
                  </div>

                  {/* Expandable Clinical Details */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-slate-200 space-y-2 animate-fadeIn text-xs text-slate-700">
                      <div className="font-bold text-navy-800">Diagnostic & Clinical Procedures:</div>
                      {area.clinicalDetails.map((detail, idx) => (
                        <div key={idx} className="flex items-start space-x-2">
                          <Check className="w-3.5 h-3.5 text-teal-600 shrink-0 mt-0.5" />
                          <span>{detail}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card Action Link */}
                <div className="mt-6 pt-4 border-t border-slate-200/70 flex items-center justify-between">
                  <button
                    onClick={() => setActiveArea(isExpanded ? null : area.id)}
                    className="text-xs font-bold text-teal-700 hover:text-teal-800 flex items-center space-x-1"
                  >
                    <span>{isExpanded ? 'Show Less' : 'View Clinical Protocols'}</span>
                    <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                  </button>

                  <a
                    href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-semibold text-slate-500 hover:text-navy-800"
                  >
                    Inquire Desk →
                  </a>
                </div>

              </div>
            );
          })}
        </div>

        {/* Reassurance Footer Banner */}
        <div className="mt-12 bg-navy-900 rounded-2xl p-6 sm:p-8 text-white flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center md:text-left">
            <h4 className="text-lg font-bold text-white">Need an Objective Opinion on Your Diagnosis or IOL Selection?</h4>
            <p className="text-xs sm:text-sm text-slate-300">
              Bring your previous biometry scans, spectacle numbers, or retinal reports for a comprehensive clinical review.
            </p>
          </div>
          <a
            href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 px-6 py-3 rounded-xl text-sm font-bold bg-teal-600 hover:bg-teal-500 text-white transition-all shadow-md"
          >
            Connect with Desk via WhatsApp
          </a>
        </div>

      </div>
    </section>
  );
};
