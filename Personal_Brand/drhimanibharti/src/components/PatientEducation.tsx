import React, { useState } from 'react';
import { DOCTOR_CONFIG, EducationalFAQ, EducationalVideo } from '../config/doctorConfig';
import { ChevronDown, Video, Play, ExternalLink, Languages, BookOpen } from 'lucide-react';

interface PatientEducationProps {
  onOpenVideo: (video: EducationalVideo) => void;
}

export const PatientEducation: React.FC<PatientEducationProps> = ({ onOpenVideo }) => {
  const [openFaqId, setOpenFaqId] = useState<number | null>(1); // 1st FAQ open by default
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [bilingualMode, setBilingualMode] = useState<'both' | 'hinglish' | 'english'>('both');

  const categories = ['All', 'Cataract', 'Retina & Diabetes', 'Pediatric & Myopia', 'Dry Eye & Lifestyle'];

  const filteredFaqs = selectedCategory === 'All'
    ? DOCTOR_CONFIG.faqs
    : DOCTOR_CONFIG.faqs.filter(f => f.category === selectedCategory);

  const toggleFaq = (id: number) => {
    setOpenFaqId(openFaqId === id ? null : id);
  };

  return (
    <section id="patient-education" className="py-20 bg-slate-50 border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-bold uppercase tracking-wider">
            <BookOpen className="w-3.5 h-3.5 text-teal-600" />
            <span>Public Health Literacy</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-navy-900 tracking-tight">
            Patient Education & Common Eye Questions
          </h2>
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed">
            Evidence-based answers to frequently asked eye health questions in English and everyday Hinglish, helping families make informed decisions about eye procedures.
          </p>

          {/* Bilingual Quick Selector */}
          <div className="pt-2 flex items-center justify-center space-x-2 text-xs">
            <span className="text-slate-500 flex items-center space-x-1 font-semibold">
              <Languages className="w-3.5 h-3.5 text-teal-600" />
              <span>Language Preference:</span>
            </span>
            <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
              <button
                onClick={() => setBilingualMode('both')}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                  bilingualMode === 'both' ? 'bg-teal-600 text-white shadow-xs' : 'text-slate-600 hover:text-navy-900'
                }`}
              >
                English + Hinglish
              </button>
              <button
                onClick={() => setBilingualMode('hinglish')}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                  bilingualMode === 'hinglish' ? 'bg-teal-600 text-white shadow-xs' : 'text-slate-600 hover:text-navy-900'
                }`}
              >
                Hinglish Only
              </button>
              <button
                onClick={() => setBilingualMode('english')}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition-all ${
                  bilingualMode === 'english' ? 'bg-teal-600 text-white shadow-xs' : 'text-slate-600 hover:text-navy-900'
                }`}
              >
                English Only
              </button>
            </div>
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                selectedCategory === cat
                  ? 'bg-navy-800 text-white shadow-sm'
                  : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Accordion FAQ Grid */}
        <div className="mt-8 max-w-4xl mx-auto space-y-4">
          {filteredFaqs.map((faq: EducationalFAQ) => {
            const isOpen = openFaqId === faq.id;
            return (
              <div
                key={faq.id}
                className={`rounded-2xl border transition-all duration-200 overflow-hidden ${
                  isOpen
                    ? 'bg-white border-teal-500/50 shadow-md ring-1 ring-teal-500/20'
                    : 'bg-white/90 border-slate-200 hover:border-slate-300'
                }`}
              >
                <button
                  onClick={() => toggleFaq(faq.id)}
                  className="w-full px-6 py-5 text-left flex items-start justify-between gap-4 focus:outline-none"
                  aria-expanded={isOpen}
                >
                  <div className="flex items-start space-x-3.5">
                    <span className="w-7 h-7 rounded-lg bg-teal-50 text-teal-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {faq.id}
                    </span>
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-teal-700 block mb-1">
                        {faq.category}
                      </span>
                      <h3 className="text-base sm:text-lg font-bold text-navy-900 leading-snug">
                        {faq.question}
                      </h3>
                    </div>
                  </div>
                  <ChevronDown
                    className={`w-5 h-5 text-slate-400 shrink-0 mt-1 transition-transform duration-200 ${
                      isOpen ? 'rotate-180 text-teal-600' : ''
                    }`}
                  />
                </button>

                {isOpen && (
                  <div className="px-6 pb-6 pt-2 border-t border-slate-100 space-y-4 text-sm text-slate-700 animate-fadeIn">
                    
                    {/* Detailed English Answer */}
                    {(bilingualMode === 'both' || bilingualMode === 'english') && (
                      <div className="leading-relaxed">
                        <p>{faq.englishAnswer}</p>
                      </div>
                    )}

                    {/* Hinglish Quick Summary Box */}
                    {(bilingualMode === 'both' || bilingualMode === 'hinglish') && (
                      <div className="p-4 rounded-xl bg-teal-50/80 border border-teal-200/90 text-xs sm:text-sm text-teal-950 space-y-1">
                        <div className="font-bold text-teal-800 flex items-center space-x-1.5 uppercase tracking-wider text-[11px]">
                          <span>🇮🇳 Saral Bhasha Mein Samjhein (Hinglish):</span>
                        </div>
                        <p className="italic leading-relaxed">{faq.hinglishSummary}</p>
                      </div>
                    )}

                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Educational Video Shelf */}
        <div className="mt-20 pt-16 border-t border-slate-200">
          <div className="max-w-3xl mx-auto text-center space-y-3 mb-10">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-navy-50 text-navy-800 text-xs font-bold uppercase tracking-wider">
              <Video className="w-3.5 h-3.5 text-teal-600" />
              <span>Visual Learning Shelf</span>
            </div>
            <h3 className="text-2xl sm:text-3xl font-extrabold text-navy-900">
              Educational Video Explainers
            </h3>
            <p className="text-xs sm:text-sm text-slate-600">
              Short, objective educational videos hosted by Dr. Himani J Bharti explaining procedures without medical jargon.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {DOCTOR_CONFIG.educationalVideos.map((video: EducationalVideo) => (
              <div
                key={video.id}
                className="group bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs hover:shadow-xl transition-all duration-300 flex flex-col justify-between"
              >
                <div>
                  {/* Thumbnail Container */}
                  <div className="relative aspect-video bg-navy-900 overflow-hidden cursor-pointer" onClick={() => onOpenVideo(video)}>
                    <img
                      src={video.thumbnailPlaceholder}
                      alt={video.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-90 group-hover:opacity-100"
                    />
                    <div className="absolute inset-0 bg-navy-950/40 group-hover:bg-navy-950/20 transition-colors flex items-center justify-center">
                      <div className="w-12 h-12 rounded-full bg-white/90 group-hover:bg-teal-500 group-hover:text-white text-navy-900 flex items-center justify-center shadow-lg transition-all group-hover:scale-110">
                        <Play className="w-5 h-5 fill-current ml-0.5" />
                      </div>
                    </div>
                    <div className="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded bg-black/75 text-white text-[11px] font-semibold">
                      {video.duration}
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="p-5 space-y-2">
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {video.tags.map(t => (
                        <span key={t} className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-semibold">
                          {t}
                        </span>
                      ))}
                    </div>
                    <h4 className="text-base font-bold text-navy-900 group-hover:text-teal-700 transition-colors line-clamp-2">
                      {video.title}
                    </h4>
                    <p className="text-xs text-slate-600 leading-relaxed line-clamp-2">
                      {video.description}
                    </p>
                  </div>
                </div>

                {/* Footer Link */}
                <div className="p-5 pt-0">
                  <a
                    href={video.youtubeUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-2.5 px-3 rounded-lg bg-slate-50 hover:bg-teal-50 text-slate-700 hover:text-teal-800 border border-slate-200 transition-colors text-xs font-semibold flex items-center justify-center space-x-1.5"
                  >
                    <span>Watch on YouTube</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>

              </div>
            ))}
          </div>

          <div className="mt-8 text-center">
            <a
              href={DOCTOR_CONFIG.socials.youtubeChannel}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 text-xs font-bold text-teal-700 hover:text-teal-800"
            >
              <span>Explore full educational video library on YouTube ({DOCTOR_CONFIG.socials.youtubeHandle})</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

        </div>

      </div>
    </section>
  );
};
