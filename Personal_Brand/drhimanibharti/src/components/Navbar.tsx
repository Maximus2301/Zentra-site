import React, { useState } from 'react';
import { DOCTOR_CONFIG } from '../config/doctorConfig';
import { MessageSquare, Menu, X, Eye } from 'lucide-react';

interface NavbarProps {
  isTextEnlarged: boolean;
  onToggleTextSize: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ isTextEnlarged, onToggleTextSize }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { name: 'Clinical Focus', href: '#clinical-focus' },
    { name: 'Where to Consult', href: '#consultation-schedule' },
    { name: 'About', href: '#about' },
    { name: 'Patient Education', href: '#patient-education' },
    { name: 'For Doctors', href: '#referring-physicians' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          
          {/* Left: Wordmark & Specialty Sub-label */}
          <a href="#" className="flex items-center space-x-3 group">
            <div className="w-11 h-11 rounded-xl bg-navy-800 text-teal-400 flex items-center justify-center shadow-inner group-hover:bg-navy-900 transition-colors">
              <Eye className="w-6 h-6 text-teal-500" />
            </div>
            <div>
              <div className="text-xl font-bold tracking-tight text-navy-800 group-hover:text-teal-700 transition-colors font-sans">
                {DOCTOR_CONFIG.identity.fullName}
              </div>
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                {DOCTOR_CONFIG.identity.specialty} • Indore, MP
              </div>
            </div>
          </a>

          {/* Center Links (Desktop) */}
          <nav className="hidden md:flex items-center space-x-7">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="text-sm font-semibold text-slate-700 hover:text-teal-600 transition-colors"
              >
                {link.name}
              </a>
            ))}
          </nav>

          {/* Right Action: Text Size Toggle + Primary CTA */}
          <div className="hidden lg:flex items-center space-x-4">
            {/* Accessibility Font Size Toggle */}
            <button
              onClick={onToggleTextSize}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all flex items-center space-x-1.5 ${
                isTextEnlarged
                  ? 'bg-teal-50 border-teal-600 text-teal-700 shadow-sm'
                  : 'bg-slate-50 border-slate-300 text-slate-700 hover:border-slate-400'
              }`}
              title="Toggle larger text for easier reading"
              aria-label="Toggle text size for readability"
            >
              <span className="text-slate-400">Text Size:</span>
              <span className="font-bold">{isTextEnlarged ? 'A+' : 'A'}</span>
            </button>

            {/* Book Consultation Primary Button */}
            <a
              href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 active:bg-teal-800 transition-all shadow-sm hover:shadow-md space-x-2"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Book Consultation</span>
            </a>
          </div>

          {/* Mobile Menu & Text Toggle Button */}
          <div className="flex items-center space-x-2 md:hidden">
            <button
              onClick={onToggleTextSize}
              className="px-2.5 py-1 text-xs font-bold rounded border border-slate-300 text-slate-700 bg-slate-50"
              aria-label="Enlarge text size"
            >
              {isTextEnlarged ? 'A+' : 'A'}
            </button>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-700 hover:bg-slate-100 focus:outline-none"
              aria-label="Toggle mobile menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>

        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-slate-200 px-4 pt-3 pb-6 space-y-3">
          <nav className="flex flex-col space-y-2">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-md text-base font-semibold text-slate-800 hover:bg-slate-100 hover:text-teal-700"
              >
                {link.name}
              </a>
            ))}
          </nav>
          <div className="pt-2 border-t border-slate-100">
            <a
              href={DOCTOR_CONFIG.communication.whatsappBookingUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full flex items-center justify-center px-4 py-3 rounded-lg text-sm font-semibold text-white bg-teal-600 hover:bg-teal-700 space-x-2"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Book Appointment (WhatsApp)</span>
            </a>
          </div>
        </div>
      )}
    </header>
  );
};
