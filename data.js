/**
 * ============================================================
 *  E-VOTING SYSTEM — DATA FILE
 *  Edit this file to change candidates, positions & school name
 * ============================================================
 */

const SCHOOL_NAME = "Mices Public School";
const ELECTION_TITLE = "Student Council Election 2026–27";

/**
 * Each position has a list of candidates.
 * To add/remove a candidate, just edit the array below.
 *
 * Fields:
 *   id       — unique number (don't repeat)
 *   name     — candidate's full name
 *   class    — their class / grade
 *   motto    — short campaign slogan
 *   photo    — path to photo file  (put photos in /photos/ folder)
 *              or leave "" to show initials avatar
 */
const ELECTION_DATA = [
  {
    position: "School President",
    icon: "👑",
    candidates: [
      { id: 1,  name: "Arjun Mehta",    class: "Class 10-A", motto: "Leading with vision, serving with heart.",       photo: "photos/m1.png" },
      { id: 2,  name: "Priya Sharma",   class: "Class 10-B", motto: "Together we rise, divided we fall.",             photo: "photos/f1.png" },
      { id: 3,  name: "Rahul Nair",     class: "Class 10-C", motto: "Your voice, my mission.",                        photo: "photos/m2.png" },
      { id: 17, name: "NOTA",           class: "None of the above.",         motto: "None of the above.",                             photo: "" },
    ]
  },
  {
    position: "Vice President",
    icon: "🌟",
    candidates: [
      { id: 4,  name: "Sneha Patel",    class: "Class 9-A",  motto: "Empowering every student every day.",            photo: "photos/f2.png" },
      { id: 5,  name: "Kiran Das",      class: "Class 9-B",  motto: "Dedication, integrity, excellence.",             photo: "photos/m3.png" },
      { id: 6,  name: "Aisha Khan",     class: "Class 9-C",  motto: "Stronger together, brighter tomorrow.",          photo: "photos/f3.png" },
      { id: 18, name: "NOTA",           class: "None of the above.",         motto: "None of the above.",                             photo: "" },
    ]
  },
  {
    position: "General Secretary",
    icon: "📋",
    candidates: [
      { id: 7,  name: "Dev Pillai",     class: "Class 9-A",  motto: "Organised, efficient, always ready.",            photo: "photos/m4.png" },
      { id: 8,  name: "Meera Joshi",    class: "Class 9-B",  motto: "Your needs, my responsibility.",                 photo: "photos/f4.png" },
      { id: 19, name: "NOTA",           class: "None of the above.",         motto: "None of the above.",                             photo: "" },
    ]
  },
  {
    position: "Treasurer",
    icon: "💰",
    candidates: [
      { id: 9,  name: "Rohan Verma",    class: "Class 8-A",  motto: "Every rupee counts, every student matters.",     photo: "photos/m1.png" },
      { id: 10, name: "Fatima Zahra",   class: "Class 8-B",  motto: "Transparent, fair and accountable.",             photo: "photos/f1.png" },
      { id: 11, name: "Nikhil Gupta",   class: "Class 8-C",  motto: "Smart spending for a better school.",            photo: "photos/m2.png" },
      { id: 20, name: "NOTA",           class: "None of the above.",         motto: "None of the above.",                             photo: "" },
    ]
  },
  {
    position: "Sports Captain",
    icon: "🏆",
    candidates: [
      { id: 12, name: "Ayesha Reddy",   class: "Class 10-A", motto: "Team spirit fuels every victory.",               photo: "photos/f2.png" },
      { id: 13, name: "Samir Bose",     class: "Class 10-B", motto: "Play hard, win together, stand united.",         photo: "photos/m3.png" },
      { id: 21, name: "NOTA",           class: "None of the above.",         motto: "None of the above.",                             photo: "" },
    ]
  },
  {
    position: "Cultural Secretary",
    icon: "🎭",
    candidates: [
      { id: 14, name: "Tanvi Iyer",     class: "Class 9-C",  motto: "Art, culture & creativity for all.",             photo: "photos/f3.png" },
      { id: 15, name: "Zara Ahmed",     class: "Class 9-A",  motto: "Celebrate diversity, inspire creativity.",        photo: "photos/f4.png" },
      { id: 16, name: "Ishaan Roy",     class: "Class 9-B",  motto: "Every talent deserves a stage.",                  photo: "photos/m4.png" },
      { id: 22, name: "NOTA",           class: "None of the above.",         motto: "None of the above.",                             photo: "" },
    ]
  }
];
