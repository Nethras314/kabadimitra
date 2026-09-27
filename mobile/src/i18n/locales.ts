// Localization: eight supported languages. English is canonical; Hindi is
// seeded. Remaining locales (mr, ta, te, ml, kn, bn) are content work.

export const SUPPORTED_LOCALES = ['hi', 'en', 'mr', 'ta', 'te', 'ml', 'kn', 'bn'] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const collectorCategories: Record<string, Record<string, string>> = {
  en: {
    tv_monitor: 'TV / Monitor',
    computer_laptop: 'Computer / Laptop',
    mobile_electronics: 'Mobile / Electronics',
    pcb_board: 'PCB / Board',
    cable_wire: 'Cable / Wire',
    battery: 'Battery',
    motor: 'Motor',
    magnet: 'Magnet',
    plastic: 'Plastic',
    metal: 'Metal',
    lamp: 'Lamp',
    printer: 'Printer',
    other: 'Other',
    dont_know: "I don't know",
  },
  hi: {
    tv_monitor: 'टीवी / मॉनिटर',
    computer_laptop: 'कंप्यूटर / लैपटॉप',
    mobile_electronics: 'मोबाइल / इलेक्ट्रॉनिक्स',
    pcb_board: 'पीसीबी / बोर्ड',
    cable_wire: 'केबल / तार',
    battery: 'बैटरी',
    motor: 'मोटर',
    magnet: 'चुंबक',
    plastic: 'प्लास्टिक',
    metal: 'धातु',
    lamp: 'लैंप',
    printer: 'प्रिंटर',
    other: 'अन्य',
    dont_know: 'मुझे नहीं पता',
  },
};
