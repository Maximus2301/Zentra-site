import React, { useEffect } from 'react';
import { EducationalVideo } from '../config/doctorConfig';
import { X, ExternalLink } from 'lucide-react';

interface VideoModalProps {
  video: EducationalVideo | null;
  onClose: () => void;
}

export const VideoModal: React.FC<VideoModalProps> = ({ video, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (video) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'auto';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [video, onClose]);

  if (!video) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl overflow-hidden shadow-2xl border border-slate-200">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 bg-navy-900 text-white">
          <div className="pr-4">
            <h4 className="text-sm font-bold truncate">{video.title}</h4>
            <p className="text-[11px] text-teal-300">Dr. Himani J Bharti • Patient Education</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-navy-800 text-slate-300 hover:text-white transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Video Preview Canvas */}
        <div className="relative aspect-video bg-black flex flex-col items-center justify-center text-center p-6 text-white space-y-4">
          <img
            src={video.thumbnailPlaceholder}
            alt={video.title}
            className="absolute inset-0 w-full h-full object-cover opacity-40 blur-xs"
          />
          <div className="relative z-10 max-w-lg space-y-3">
            <span className="px-2.5 py-1 rounded bg-teal-600 text-white text-xs font-bold uppercase tracking-wider">
              Educational Guide
            </span>
            <h3 className="text-lg sm:text-xl font-bold">{video.title}</h3>
            <p className="text-xs text-slate-200 leading-relaxed">{video.description}</p>
            <div className="pt-2">
              <a
                href={video.youtubeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center px-6 py-3 rounded-xl bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold space-x-2 shadow-lg transition-all"
              >
                <span>Watch Full Explainer on YouTube</span>
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 text-center text-xs text-slate-500">
          Educational content only • Does not substitute in-person ophthalmology diagnosis.
        </div>

      </div>
    </div>
  );
};
