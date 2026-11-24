/**
 * Centralized Configuration for Dr. Himani J Bharti's Medical Web Platform
 * 
 * Update contact details, host clinic locations, OPD timings, NMC registration,
 * FAQs, and video links here. Any update here reflects across the entire website instantly.
 */

export interface ClinicLocation {
  id: string;
  isPrimary: boolean;
  statusBadge: string;
  name: string;
  tagline?: string;
  locality: string;
  fullAddress: string;
  landmark?: string;
  city: string;
  state: string;
  pincode?: string;
  timings: {
    days: string;
    morningSlot?: string;
    eveningSlot?: string;
    fullTimingString: string;
  };
  phoneDesk: string;
  phoneDeskDisplay: string;
  whatsappDesk: string;
  googleMapsUrl: string;
  note?: string;
}

export interface ClinicalFocusArea {
  id: string;
  title: string;
  iconName: string;
  shortSummary: string;
  clinicalDetails: string[];
  keyInsight: string;
}

export interface EducationalFAQ {
  id: number;
  question: string;
  englishAnswer: string;
  hinglishSummary: string;
  category: 'Cataract' | 'Retina & Diabetes' | 'Pediatric & Myopia' | 'Dry Eye & Lifestyle';
}

export interface EducationalVideo {
  id: string;
  title: string;
  description: string;
  thumbnailPlaceholder: string;
  duration: string;
  youtubeUrl: string;
  tags: string[];
}

export const DOCTOR_CONFIG = {
  // 1. Mandatory Identity & NMC Credentialing (Oct 2026 Regulations)
  identity: {
    fullName: "Dr. Himani J Bharti",
    shortName: "Dr. Himani Bharti",
    specialty: "Ophthalmologist",
    superSpecialtySummary: "Cataract Evaluation, Diabetic Retinopathy Screening & Comprehensive Eye Care",
    degrees: "MBBS, MS (Ophthalmology)",
    degreeNote: "[MBBS, MS (Ophthalmology) — Update Exact Degrees]",
    registrationNumber: "[MP Medical Council / NMC Reg. No.: XXXXX]",
    medicalCouncil: "Madhya Pradesh Medical Council / National Medical Commission (NMC)",
    cityOfPractice: "Indore, Madhya Pradesh",
    experienceYears: "Clinical Specialist",
    bilingualCare: "Consultations in Hindi & English",
  },

  // 2. Direct Communication & Appointment Desks
  communication: {
    officialWebsite: "https://drhimanibharti.com",
    primaryPhone: "+91XXXXXXXXXX",
    primaryPhoneDisplay: "+91 XXXXX XXXXX",
    whatsappDeskNumber: "91XXXXXXXXXX",
    whatsappPreFilledText: "Hello Dr. Himani J Bharti's Desk, I would like to inquire about an eye consultation in Indore.",
    get whatsappBookingUrl() {
      return `https://wa.me/${this.whatsappDeskNumber}?text=${encodeURIComponent(this.whatsappPreFilledText)}`;
    },
    officialEmail: "desk@drhimanibharti.com",
    peerLiaisonEmail: "referrals@drhimanibharti.com",
  },

  // 3. Social Media & Digital Directory Links
  socials: {
    youtubeChannel: "https://www.youtube.com/@drhimanijbharti",
    youtubeHandle: "@drhimanijbharti",
    instagramProfile: "https://www.instagram.com/drhimanibharti",
    instagramHandle: "@drhimanibharti",
    linkedinProfile: "https://www.linkedin.com/in/drhimanijbharti",
    googleBusinessProfile: "https://maps.google.com/?q=Dr+Himani+J+Bharti+Ophthalmologist+Indore",
  },

  // 4. Hero Section Copy
  hero: {
    badge: "OPHTHALMOLOGY & EYE CARE • INDORE",
    headline: "Dr. Himani J Bharti",
    credentialsLine: "MBBS, MS (Ophthalmology) | Reg. No: [MP Medical Council / NMC Reg. No.]",
    subheadline: "Clear, compassionate, and evidence-based eye care—helping patients and families in Indore make informed decisions about cataract, diabetic eye health, and lifelong vision.",
    primaryButtonText: "Book an Appointment (WhatsApp)",
    secondaryButtonText: "View Consultation Timings",
    consultationPill: "Unhurried Consultations • Transparent Counseling",
  },

  // 5. Clinical Focus Areas (6 Essential Non-Promotional Pillars)
  clinicalFocusAreas: [
    {
      id: "cataract-counseling",
      title: "Cataract Evaluation & Lens Counseling",
      iconName: "Eye",
      shortSummary: "Comprehensive pre-operative assessment and unbiased guidance on Monofocal, Toric, EDOF, and Multifocal intraocular lenses.",
      clinicalDetails: [
        "Slit-lamp biomicroscopic evaluation of cataract grade and ocular health",
        "Corneal curvature and pre-existing astigmatism assessment",
        "Objective counseling on intraocular lens (IOL) options suited to daily lifestyle",
        "Clear post-operative recovery instructions and expectation setting",
      ],
      keyInsight: "Surgery timing is personalized to when blurry vision or night glare interferes with your routine—never rushed.",
    },
    {
      id: "diabetic-retinopathy",
      title: "Diabetic Retinopathy Screening",
      iconName: "HeartPulse",
      shortSummary: "Routine dilated fundus evaluations and preventive monitoring for diabetic patients to protect long-term retinal health.",
      clinicalDetails: [
        "Pharmacological pupil dilation for peripheral retinal inspection",
        "Screening for microaneurysms, retinal hemorrhages, and macular edema",
        "Structured clinical reporting shared with treating diabetologists/physicians",
        "Annual preventive surveillance protocols to detect silent changes early",
      ],
      keyInsight: "Retinal micro-vessels can suffer micro-damage without early pain or vision loss. Annual screening is essential.",
    },
    {
      id: "glaucoma-management",
      title: "Glaucoma Diagnosis & Management",
      iconName: "ShieldCheck",
      shortSummary: "Intraocular pressure monitoring, optic nerve evaluation, and long-term medical management to safeguard peripheral vision.",
      clinicalDetails: [
        "Applanation tonometry for accurate intraocular pressure measurement",
        "Optic nerve cup-to-disc ratio documentation and progression tracking",
        "Visual field assessment referrals and medical IOP lowering regimens",
        "Patient education on adherence to daily ocular hypotensive drops",
      ],
      keyInsight: "Often called the silent thief of sight; proactive IOP monitoring helps prevent irreversible optic nerve damage.",
    },
    {
      id: "pediatric-myopia",
      title: "Pediatric Eye Care & Myopia Control",
      iconName: "Users",
      shortSummary: "Vision screening for school-age children, refractive error correction, and evidence-based myopia progression guidance.",
      clinicalDetails: [
        "Child-friendly visual acuity assessment and cycloplegic refraction",
        "Guidance on outdoor daylight exposure (90–120 mins/day) to slow axial elongation",
        "20-20-20 screen ergonomics coaching for children and parents",
        "Monitoring progressive nearsightedness at regular 6-month intervals",
      ],
      keyInsight: "Early identification of refractive errors prevents amblyopia (lazy eye) and fosters comfortable classroom learning.",
    },
    {
      id: "dry-eye-cvs",
      title: "Dry Eye & Computer Vision Syndrome",
      iconName: "Sparkles",
      shortSummary: "Targeted tear-film assessment and relief protocols for digital screen strain and ocular surface discomfort.",
      clinicalDetails: [
        "Evaluation of tear breakup time (TBUT) and ocular surface staining",
        "Blink dynamics coaching for IT professionals and high-screen users",
        "Preservative-free tear substitute guidance and environmental adjustments",
        "Targeted management of meibomian gland dysfunction (MGD)",
      ],
      keyInsight: "Screen use reduces blink rates by 50%. A systematic ergonomics and lubrication strategy restores ocular comfort.",
    },
    {
      id: "comprehensive-cornea",
      title: "Comprehensive Eye Checkups & Cornea Care",
      iconName: "Stethoscope",
      shortSummary: "Routine refraction, corneal infection management, ocular allergy care, and preventive ocular health exams.",
      clinicalDetails: [
        "Accurate spectacle power determination for distance and presbyopia",
        "Diagnosis and targeted medical management of infectious keratitis and conjunctivitis",
        "Seasonal ocular allergy relief and ocular surface maintenance",
        "Baseline visual health documentation for patients across all age brackets",
      ],
      keyInsight: "Preventive eye examinations catch asymptomatic refractive and surface issues before they cause headaches or strain.",
    },
  ] as ClinicalFocusArea[],

  // 6. Portable "Where to Consult" Practice Locations (Configurable Array)
  practiceLocations: [
    {
      id: "indore-active-host-clinic",
      isPrimary: true,
      statusBadge: "Active OPD Location",
      name: "[Host Clinic Name, Indore]",
      tagline: "Outpatient Ophthalmology Consultations",
      locality: "Scheme 140 / Vijay Nagar Area",
      fullAddress: "[Clinic Address Line 1, Near Landmark, Scheme 140 / Vijay Nagar, Indore, Madhya Pradesh - 452016]",
      landmark: "Easily accessible from AB Road and Ring Road",
      city: "Indore",
      state: "Madhya Pradesh",
      timings: {
        days: "Monday – Saturday",
        morningSlot: "10:30 AM – 2:00 PM",
        eveningSlot: "5:30 PM – 8:00 PM",
        fullTimingString: "Monday – Saturday | 10:30 AM – 2:00 PM & 5:30 PM – 8:00 PM",
      },
      phoneDesk: "+91XXXXXXXXXX",
      phoneDeskDisplay: "+91 XXXXX XXXXX",
      whatsappDesk: "91XXXXXXXXXX",
      googleMapsUrl: "https://maps.google.com/?q=Dr+Himani+J+Bharti+Ophthalmologist+Indore",
      note: "Prior appointment recommended for dilated retinal examinations and cataract biometry evaluations.",
    },
    {
      id: "indore-scheme140-independent",
      isPrimary: false,
      statusBadge: "Upcoming Dedicated Clinic",
      name: "Dr. Himani J Bharti Comprehensive Eye Clinic",
      tagline: "Independent Practice Transitioning Soon",
      locality: "Scheme 140, Indore",
      fullAddress: "Scheme 140, Indore, Madhya Pradesh - 452016",
      city: "Indore",
      state: "Madhya Pradesh",
      timings: {
        days: "Upcoming Practice",
        fullTimingString: "Announcing Soon • Advance Inquiries Welcome",
      },
      phoneDesk: "+91XXXXXXXXXX",
      phoneDeskDisplay: "+91 XXXXX XXXXX",
      whatsappDesk: "91XXXXXXXXXX",
      googleMapsUrl: "https://maps.google.com/?q=Scheme+140+Indore",
      note: "Designed with modern outpatient diagnostics, spacious counseling suites, and accessible ground-floor entry for senior citizens.",
    },
  ] as ClinicLocation[],

  // 7. About Bio & Credentials
  about: {
    headline: "About Dr. Himani J Bharti",
    subheadline: "Ophthalmologist • Comprehensive Eye Care, Cataract Counseling & Retinal Screening in Indore",
    bioParagraphs: [
      "Dr. Himani J Bharti is a dedicated ophthalmologist practicing in Indore, committed to providing clear, unhurried, and evidence-based eye care for patients across all age groups.",
      "Her clinical approach centers on patient education and informed decision-making. Whether evaluating a senior citizen for cataract (motiabind) surgery, conducting routine diabetic retinopathy screenings, or managing refractive errors and digital eye strain, Dr. Himani J Bharti ensures that every patient and their family clearly understand their diagnostic findings in simple Hindi or English before deciding on treatment.",
      "By combining thorough diagnostic evaluation with transparent counseling on medical and surgical options, she focuses on helping individuals preserve and protect their long-term vision safely.",
    ],
    credentials: [
      {
        label: "Qualifications",
        value: "MBBS, MS (Ophthalmology) — [Update Exact Degrees]",
      },
      {
        label: "Registration Status",
        value: "Registered Medical Practitioner — [MP Medical Council / NMC Reg. No.: XXXXX]",
      },
      {
        label: "Clinical Focus",
        value: "Cataract Evaluation & IOL Counseling, Diabetic Retinopathy Screening, Glaucoma Care, Pediatric Myopia & Dry Eye Management",
      },
      {
        label: "Professional Memberships",
        value: "[All India Ophthalmological Society (AIOS) / Madhya Pradesh State Ophthalmological Society]",
      },
      {
        label: "Languages Spoken",
        value: "Hindi, English (Clear bilingual consultations)",
      },
    ],
    clinicalPhilosophy: [
      {
        title: "Clear Communication",
        desc: "Diagnostic findings are explained without jargon so patients understand the exact health of their eyes.",
      },
      {
        title: "Evidence-Based Guidance",
        desc: "All surgical and medical recommendations adhere to verified clinical guidelines.",
      },
      {
        title: "Family-Centered Decisions",
        desc: "We encourage family involvement during cataract IOL counseling so everyone is aligned comfortably.",
      },
    ],
  },

  // 8. Bilingual Patient Education FAQs (Exact English + Hinglish Summaries)
  faqs: [
    {
      id: 1,
      category: "Cataract",
      question: "When is the right time to undergo Cataract (Motiabind) surgery?",
      englishAnswer: "Cataract surgery does not always need to be rushed the moment a mild clouding of the natural lens is detected. The right time is typically when blurred vision, glare while driving at night, or difficulty reading begins interfering with your daily routine and independence. Waiting until a cataract becomes overly mature ('pakka motiabind') can make surgery technically more complex, so periodic eye checkups help determine the safest window for your eyes.",
      hinglishSummary: "Motiabind ka operation tab zaroori hota hai jab dhundhlapan ya raat ki driving mein glare aapke rozmarra ke kaam mein rukawat daalne lage. Motiabind ko bahut zyada pakne tak nahi rokna chahiye; regular checkup se sahi samay tay kiya jaata hai.",
    },
    {
      id: 2,
      category: "Cataract",
      question: "How do I choose between a Monofocal, Toric, and Multifocal lens?",
      englishAnswer: "Intraocular lens (IOL) selection depends on your lifestyle, corneal measurements, and retinal health—not a one-size-fits-all rule. Monofocal lenses provide sharp distance vision (reading glasses are usually needed afterward), Toric lenses correct pre-existing cylindrical power (astigmatism), and EDOF / Multifocal lenses aim to reduce spectacle dependence across distance and near tasks. A detailed pre-operative biometry scan helps identify which lens aligns safely with your eye structure.",
      hinglishSummary: "Sahi lens ka chunaav aapki aankh ki jaanch (biometry) aur lifestyle par nirbhar karta hai. Monofocal door ki nazar saaf karta hai (padhne ke liye chashma lagta hai), Toric cylindrical number theek karta hai, aur Multifocal/EDOF chashme ki nirbharta kam karne mein madad karte hain.",
    },
    {
      id: 3,
      category: "Retina & Diabetes",
      question: "Why do diabetic patients need an annual dilated retina checkup even with clear vision?",
      englishAnswer: "High blood sugar can gradually affect tiny blood vessels at the back of the eye (Diabetic Retinopathy) without causing any pain or early vision loss. By the time blurry vision appears, retinal changes may already be advanced. A routine annual dilated fundus examination detects early swelling or vessel changes on time, allowing timely preventive care.",
      hinglishSummary: "Diabetes mein bina kisi dard ya dhundhlepan ke parde (retina) ki naso mein asar ho sakta hai. Isliye nazar bilkul saaf hone par bhi saal mein ek baar parda phaila kar (dilated) retina checkup karana zaroori hai.",
    },
    {
      id: 4,
      category: "Cataract",
      question: "Can eye drops or medicines dissolve a cataract without surgery?",
      englishAnswer: "Currently, no scientifically proven eye drops, tablets, or exercises can reverse or dissolve a cataract once the natural lens proteins have clouded. In very early stages, updating eyeglass prescriptions and improving lighting can help you see comfortably, while surgery remains the established medical method to replace a clouded lens.",
      hinglishSummary: "Abhi tak aisi koi eye drop ya dawa uplabdh nahi hai jo bane hue motiabind ko ghula sake. Shuruati daur mein chashme ka number badal kar kaam chalaya ja sakta hai, lekin motiabind ka sthayi samadhaan operation hi hai.",
    },
    {
      id: 5,
      category: "Pediatric & Myopia",
      question: "How can parents help slow down increasing glasses power (myopia) in children?",
      englishAnswer: "Rising nearsightedness (myopia) in school-age children is linked to prolonged near-screen work and reduced outdoor time. Encouraging at least 90–120 minutes of daily outdoor daylight play, following the 20-20-20 screen break rule, maintaining proper reading distance, and scheduling 6-monthly eye exams help monitor and manage myopia progression.",
      hinglishSummary: "Bachon mein badhte chashme ke number ko control karne ke liye roz kam se kam 1.5–2 ghante bahar din ki roshni mein khelna, mobile/screen se har 20 minute mein break lena, aur har 6 mahine mein eye checkup karana bahut zaroori hai.",
    },
    {
      id: 6,
      category: "Dry Eye & Lifestyle",
      question: "What causes persistent burning and dryness during long laptop or mobile hours?",
      englishAnswer: "When focusing intently on digital screens, our natural blink rate drops by nearly half, causing the tear film to evaporate quickly and triggering burning, grittiness, or watery eyes (Computer Vision Syndrome). Proper screen ergonomics, conscious blinking, limiting direct AC airflow toward the face, and a tear-film evaluation help relieve ocular surface strain safely.",
      hinglishSummary: "Laptop ya mobile dekhte waqt palkein kam jhapakne se aankhon ki nami sookhne lagti hai, jisse jalan aur thakan hoti hai. Sahi screen distance, 20-20-20 rule, aur aankh ki nami ki jaanch se isse aaraam milta hai.",
    },
  ] as EducationalFAQ[],

  // 9. Educational Video Shelf
  educationalVideos: [
    {
      id: "vid-cataract-guide",
      title: "Understanding Cataract: When Is Surgery Really Needed?",
      description: "A simple, jargon-free guide in Hindi explaining how cataracts form and how to choose the right surgical window.",
      thumbnailPlaceholder: "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=800&q=80",
      duration: "5:20",
      youtubeUrl: "https://www.youtube.com/@drhimanijbharti",
      tags: ["Cataract Care", "Hindi Education", "Patient Guide"],
    },
    {
      id: "vid-diabetic-eye",
      title: "Diabetic Retinopathy: Why Annual Dilated Exams Matter",
      description: "Visual explanation of how high blood sugar impacts retinal micro-vessels and why early detection preserves sight.",
      thumbnailPlaceholder: "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=800&q=80",
      duration: "6:15",
      youtubeUrl: "https://www.youtube.com/@drhimanijbharti",
      tags: ["Diabetic Eye", "Preventive Screening", "Retina"],
    },
    {
      id: "vid-screen-strain",
      title: "Screen Strain & Dry Eyes: The 20-20-20 Protocol",
      description: "Practical steps to relieve digital eye strain, improve blink rates, and protect children from rapid myopia progression.",
      thumbnailPlaceholder: "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=800&q=80",
      duration: "4:45",
      youtubeUrl: "https://www.youtube.com/@drhimanijbharti",
      tags: ["Digital Health", "Myopia Control", "Pediatric"],
    },
  ] as EducationalVideo[],

  // 10. Referring Physicians Strip (B2B Healthcare Peers)
  referringPhysicians: {
    heading: "For Referring Physicians, Diabetologists & Optometrists",
    subheading: "Collaborative and ethical co-management across Indore",
    description: "Dr. Himani J Bharti collaborates with general physicians, diabetologists, and optical practitioners across Indore for timely diabetic retinopathy screening, cataract co-management, and structured clinical feedback reports.",
    benefits: [
      "Prompt dilated fundus screening reports for diabetic patient charts",
      "Objective IOL counseling feedback following pre-operative biometry",
      "Clear post-procedure discharge notes and continuity of patient care",
    ],
    buttonText: "Connect via WhatsApp for Clinical Co-Management",
    emailButtonText: "Email Medical Records Desk",
  },

  // 11. Footer & Statutory Compliance (NMC India Oct 2026)
  footer: {
    disclaimer: "Medical Disclaimer: The clinical information and educational resources provided on this website are intended solely for general patient awareness and health literacy. They do not constitute formal medical diagnosis or establish a doctor-patient relationship. Patients are advised to consult an ophthalmologist in person for comprehensive clinical examination and tailored medical advice.",
    copyright: "© 2026 Dr. Himani J Bharti. All rights reserved.",
    regulatoryNote: "Compliant with National Medical Commission (NMC) India Registered Medical Practitioner Regulations (06 Oct 2026). No promotional claims or patient testimonials.",
  },
};
