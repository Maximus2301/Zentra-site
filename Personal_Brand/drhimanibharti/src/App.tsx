import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { ClinicalFocus } from './components/ClinicalFocus';
import { ConsultationSchedule } from './components/ConsultationSchedule';
import { AboutSection } from './components/AboutSection';
import { PatientEducation } from './components/PatientEducation';
import { ReferringPhysicians } from './components/ReferringPhysicians';
import { Footer } from './components/Footer';
import { VideoModal } from './components/VideoModal';
import { EducationalVideo } from './config/doctorConfig';

export const App: React.FC = () => {
  const [isTextEnlarged, setIsTextEnlarged] = useState<boolean>(false);
  const [activeVideo, setActiveVideo] = useState<EducationalVideo | null>(null);

  const toggleTextSize = () => {
    setIsTextEnlarged(prev => {
      const next = !prev;
      if (next) {
        document.documentElement.classList.add('font-enlarged');
      } else {
        document.documentElement.classList.remove('font-enlarged');
      }
      return next;
    });
  };

  useEffect(() => {
    // Cleanup on unmount if any
    return () => {
      document.documentElement.classList.remove('font-enlarged');
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[#F8FAFC] text-[#1E293B]">
      
      {/* Sticky Navigation with Accessibility A/A+ toggle */}
      <Navbar
        isTextEnlarged={isTextEnlarged}
        onToggleTextSize={toggleTextSize}
      />

      {/* Main Page Layout */}
      <main className="flex-grow">
        
        {/* Section 1: Hero Section */}
        <Hero />

        {/* Section 2: Clinical Focus Areas (6 Core Pillars) */}
        <ClinicalFocus />

        {/* Section 3: Portable "Where to Consult" OPD Schedule */}
        <ConsultationSchedule />

        {/* Section 4: Academic & Clinical Credibility (About Bio) */}
        <AboutSection />

        {/* Section 5: Bilingual Patient Education FAQs & Video Shelf */}
        <PatientEducation
          onOpenVideo={(video) => setActiveVideo(video)}
        />

        {/* Section 6: Referring Physicians Liaison Strip */}
        <ReferringPhysicians />

      </main>

      {/* Section 7: Statutory Compliance Footer */}
      <Footer />

      {/* Educational Video Overlay Modal */}
      <VideoModal
        video={activeVideo}
        onClose={() => setActiveVideo(null)}
      />

    </div>
  );
};

export default App;
