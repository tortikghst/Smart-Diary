import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, ChevronDown, Check } from "lucide-react";
import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";
import bgImage from '../assets/bg.png';

// --- ИМПОРТЫ КАРТИНОК МАСКОТОВ ---
import mathImg from '../assets/mascots/math.png';
import russianImg from '../assets/mascots/russian.png';
import literatureImg from '../assets/mascots/literature.png';
import historyImg from '../assets/mascots/history.png';
import geographyImg from '../assets/mascots/geography.png';
import chemistryImg from '../assets/mascots/chemistry.png';
import informaticsImg from '../assets/mascots/informatics.png';
import peImg from '../assets/mascots/PE.png';
import trudImg from '../assets/mascots/trud.png';
import defaultImg from '../assets/mascots/default.png';
import phisyc from '../assets/mascots/phisycs.png';
import biol from '../assets/biol.png';
import english from '../assets/english.png';
interface UserProfile {
    full_name: string;
    class_id: number;
}

interface Subject {
    subject_id: number;
    name: string;
}

interface MascotData {
    subject_id: number;
    mascot_type: string;
    current_streak: number;
    message: string;
}

interface StreakData {
    subject_id: number;
    subject_name: string;
    current_streak: number;
}

const getDaysText = (count: number) => {
    const lastDigit = count % 10;
    const lastTwo = count % 100;
    if (lastDigit === 1 && lastTwo !== 11) return `${count} день`;
    if ([2, 3, 4].includes(lastDigit) && ![12, 13, 14].includes(lastTwo)) return `${count} дня`;
    return `${count} дней`;
};

const getMascotImage = (subjectName: string) => {
    if (!subjectName || subjectName === 'Загрузка...') return null;
    const name = subjectName.toLowerCase();

    if (name.includes('матем')) return mathImg;
    if (name.includes('русск')) return russianImg;
    if (name.includes('литерат')) return literatureImg;
    if (name.includes('истори')) return historyImg;
    if (name.includes('географ')) return geographyImg;
    if (name.includes('хими')) return chemistryImg;
    if (name.includes('информ')) return informaticsImg;
    if (name.includes('физкульт') || name.includes('физ. культ') || (name.includes('физ') && name.includes('культур'))) {
        return peImg;
    }
    if (name.includes('труд') || name.includes('технолог')) return trudImg;
    if (name.includes('физ')) return phisyc;
    if (name.includes('биолог')) return biol;
    if (name.includes('английск') || name.includes('иностран')) return english;
    return defaultImg;
};

export default function StudentMascot() {
    const navigate = useNavigate();

    const [user, setUser] = useState<UserProfile | null>(null);
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [mascot, setMascot] = useState<MascotData | null>(null);

    const [activeIndex, setActiveIndex] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [isMascotLoading, setIsMascotLoading] = useState(false);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    // 1. Загрузка профиля, списка предметов и стриков для авто-выбора
    useEffect(() => {
        const fetchInitialData = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) return;
            const headers = { 'Authorization': `Bearer ${token}` };

            try {
                const [userRes, dashRes, streaksRes] = await Promise.all([
                    fetch('/api/v1/users/me', { headers }),
                    fetch('/api/v1/student/dashboard', { headers }),
                    fetch('/api/v1/student/streaks', { headers }) // Запрашиваем стрики всех предметов
                ]);

                if (userRes.ok) setUser(await userRes.json());

                if (dashRes.ok) {
                    const dashData = await dashRes.json();
                    const fetchedSubjects: Subject[] = dashData.subjects || [];
                    setSubjects(fetchedSubjects);

                    if (fetchedSubjects.length > 0) {
                        let initialSubjectId = fetchedSubjects[0].subject_id;
                        let initialIndex = 0;

                        // Ищем предмет с максимальным стриком
                        if (streaksRes.ok) {
                            const streaksData: StreakData[] = await streaksRes.json();
                            if (streaksData.length > 0) {
                                // Находим максимальный стрик
                                const maxStreakItem = streaksData.reduce((prev, current) =>
                                    (prev.current_streak > current.current_streak) ? prev : current
                                );

                                // Ищем его индекс в общем списке предметов
                                const foundIndex = fetchedSubjects.findIndex(s => s.subject_id === maxStreakItem.subject_id);

                                // Если нашли и стрик больше нуля — выбираем его
                                if (foundIndex !== -1 && maxStreakItem.current_streak > 0) {
                                    initialIndex = foundIndex;
                                    initialSubjectId = maxStreakItem.subject_id;
                                }
                            }
                        }

                        // Устанавливаем активный индекс и грузим маскота
                        setActiveIndex(initialIndex);
                        fetchMascotData(initialSubjectId);
                    } else {
                        setIsLoading(false);
                    }
                }
            } catch (err) {
                console.error("Ошибка загрузки данных:", err);
                setIsLoading(false);
            }
        };

        fetchInitialData();
    }, []);

    const fetchMascotData = async (subjectId: number) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        setIsMascotLoading(true);

        try {
            const res = await fetch(`/api/v1/student/mascot?subject_id=${subjectId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                setMascot(await res.json());
            }
        } catch (err) {
            console.error("Ошибка загрузки маскота:", err);
        } finally {
            setIsMascotLoading(false);
            setIsLoading(false);
        }
    };

    const handlePrev = () => {
        if (activeIndex > 0) {
            const newIndex = activeIndex - 1;
            setActiveIndex(newIndex);
            fetchMascotData(subjects[newIndex].subject_id);
        }
    };

    const handleNext = () => {
        if (activeIndex < subjects.length - 1) {
            const newIndex = activeIndex + 1;
            setActiveIndex(newIndex);
            fetchMascotData(subjects[newIndex].subject_id);
        }
    };

    const handleSelectSubject = (index: number) => {
        setActiveIndex(index);
        setIsDropdownOpen(false);
        fetchMascotData(subjects[index].subject_id);
    };

    if (isLoading) {
        return <div className="min-h-screen flex items-center justify-center bg-[#f2f6f9] text-[#3b506c] font-bold">Загрузка...</div>;
    }

    const currentSubjectName = subjects[activeIndex]?.name || "Предмет не найден";
    const currentImage = getMascotImage(currentSubjectName);

    return (
        <div className="relative min-h-screen bg-[#f2f6f9] overflow-x-hidden flex justify-center font-sans">
            <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <div className="relative z-10 w-full max-w-[430px] flex flex-col pb-10">

                {/* Шапка с огоньком */}
                <header className="bg-[#B2CDE0] px-5 py-4 rounded-b-[40px] shadow-sm flex justify-between items-center min-h-[90px]">
                    <button
                        onClick={() => navigate('/student')}
                        className="w-10 h-10 bg-[#94A9BE] rounded-xl flex items-center justify-center text-white hover:bg-[#859bb1] transition-colors"
                    >
                        <ChevronLeft size={24} />
                    </button>

                    <div className="text-[#3b506c] text-center">
                        <h2 className="text-[17px] font-extrabold leading-tight">{user?.full_name || "Ученик"}</h2>
                        <p className="text-[14px] font-semibold text-[#556b86] mt-0.5">
                            Ученик {user?.class_id === 1 ? '7А' : user?.class_id === 2 ? '7Б' : user?.class_id === 3 ? '8А' : user?.class_id === 4 ? '8Б' : user?.class_id === 5 ? '9А' : '9Б'} класса
                        </p>
                    </div>

                    <div className="relative w-[60px] h-[56px] flex items-center justify-center cursor-default">
                        <svg viewBox="0 0 70 64" className="absolute inset-0 w-full h-full pointer-events-none" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect width="70" height="64" x="0" y="0" />
                            <path d="M10.1047 54.7613C14.3761 58.6666 21.2507 58.6666 35 58.6666C48.7492 58.6666 55.624 58.6666 59.8952 54.7613C64.1667 50.8562 64.1667 44.5706 64.1667 32C64.1667 19.4292 64.1667 13.1438 59.8952 9.23857C55.624 5.33331 48.7492 5.33331 35 5.33331C21.2507 5.33331 14.3761 5.33331 10.1047 9.23857C5.83334 13.1438 5.83334 19.4292 5.83334 32C5.83334 44.5706 5.83334 50.8562 10.1047 54.7613Z" fill="#94A9BE" />
                            <path d="M55.1515 32.9859C55.1515 48.8759 40.8214 52.8485 33.6567 52.8485C27.3872 52.8485 14.8485 48.8759 14.8485 32.9859C14.8485 26.075 19.1324 21.6872 22.7315 19.4787C24.377 18.469 26.4236 19.1143 26.5299 20.9369C26.7627 24.9246 30.0887 28.1281 32.6644 24.9212C35.0218 21.9859 36.1853 18.0001 36.1853 15.6065C36.1853 12.0805 40.0479 9.83991 43.0638 12.0002C48.942 16.2109 55.1515 23.2629 55.1515 32.9859Z" fill="#1c274c" />
                        </svg>
                        <span className="relative z-10 text-white text-[20px] font-black pb-1 mt-1 pointer-events-none">
                            {mascot?.current_streak || 0}
                        </span>
                    </div>
                </header>

                <div className="text-center mt-6">
                    <h1 className="text-[24px] font-extrabold text-[#3b506c]">Серия</h1>
                </div>

                {/* Карточка с маскотом */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="mt-4 mx-4"
                >
                    <Card className="bg-white/80 backdrop-blur-md rounded-[40px] shadow-sm border-none overflow-hidden pt-8 pb-6 px-4">
                        <CardContent className="flex flex-col items-center p-0">

                            <h2 className="text-[34px] font-black text-[#3b506c] mb-2">
                                {getDaysText(mascot?.current_streak || 0)}!
                            </h2>

                            <div className="w-[220px] h-[220px] flex items-center justify-center relative my-4">
                                {isMascotLoading || !currentImage ? (
                                    <div className="w-12 h-12 border-4 border-[#B2CDE0] border-t-transparent rounded-full animate-spin"></div>
                                ) : (
                                    <motion.div
                                        animate={{ y: [0, -12, 0] }}
                                        transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
                                        className="w-full h-full"
                                    >
                                        <AnimatePresence mode="wait">
                                            <motion.img
                                                key={currentSubjectName}
                                                initial={{ opacity: 0, scale: 0.8 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                exit={{ opacity: 0, scale: 0.8 }}
                                                transition={{ duration: 0.3 }}
                                                src={currentImage}
                                                alt="Маскот"
                                                className="w-full h-full object-contain drop-shadow-xl"
                                            />
                                        </AnimatePresence>
                                    </motion.div>
                                )}
                            </div>

                            <div className="h-10 flex items-center justify-center mb-2 px-4 text-center">
                                <p className="text-[14px] font-bold text-[#859bb1] leading-tight">
                                    {mascot?.message || "Продолжай в том же духе!"}
                                </p>
                            </div>

                            <div className="flex flex-col items-center gap-3 w-full mt-2">
                                <div className="flex justify-between items-center w-full max-w-[280px] bg-[#f7fafc] rounded-full px-4 py-2 border border-[#e2eaf1]">
                                    <button
                                        onClick={handlePrev}
                                        disabled={activeIndex === 0}
                                        className={`${activeIndex === 0 ? 'text-gray-300' : 'text-[#3b506c] hover:text-[#94A9BE]'} transition-colors`}
                                    >
                                        <ChevronLeft size={24}/>
                                    </button>

                                    <div className="text-center">
                                        <span className="text-[10px] font-bold text-[#94A9BE] uppercase tracking-wider block -mb-0.5">Предмет</span>
                                        <span className="text-[16px] font-extrabold text-[#3b506c]">{currentSubjectName}</span>
                                    </div>

                                    <button
                                        onClick={handleNext}
                                        disabled={activeIndex === subjects.length - 1}
                                        className={`${activeIndex === subjects.length - 1 ? 'text-gray-300' : 'text-[#3b506c] hover:text-[#94A9BE]'} transition-colors`}
                                    >
                                        <ChevronRight size={24}/>
                                    </button>
                                </div>

                                <Button
                                    onClick={() => setIsDropdownOpen(true)}
                                    className="bg-[#B2CDE0]/50 hover:bg-[#B2CDE0] text-[#3b506c] font-extrabold text-[13px] rounded-full px-5 py-1.5 h-auto flex items-center gap-1.5 transition-all mt-1"
                                >
                                    Все предметы
                                    <ChevronDown size={14} />
                                </Button>
                            </div>

                        </CardContent>
                    </Card>
                </motion.div>
            </div>

            {/* Выпадающая панель (Bottom Sheet) */}
            <AnimatePresence>
                {isDropdownOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
                            onClick={() => setIsDropdownOpen(false)}
                        />

                        <motion.div
                            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
                            transition={{ type: "spring", damping: 25, stiffness: 200 }}
                            className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-[40px] p-6 pb-10 shadow-2xl flex flex-col items-center max-w-[430px] mx-auto"
                        >
                            <div className="w-12 h-1.5 bg-gray-200 rounded-full mb-6" />
                            <h3 className="text-[20px] font-extrabold text-[#3b506c] mb-4">Выбери предмет</h3>

                            <div className="w-full flex flex-col gap-2 max-h-[50vh] overflow-y-auto no-scrollbar">
                                {subjects.map((sub, idx) => {
                                    const isActive = idx === activeIndex;
                                    return (
                                        <button
                                            key={sub.subject_id}
                                            onClick={() => handleSelectSubject(idx)}
                                            className={`w-full flex items-center justify-between p-4 rounded-[20px] font-bold text-[16px] transition-colors ${
                                                isActive
                                                    ? 'bg-[#B2CDE0] text-[#3b506c]'
                                                    : 'bg-[#f2f6f9] text-[#556b86] hover:bg-[#e2eaf1]'
                                            }`}
                                        >
                                            {sub.name}
                                            {isActive && <Check size={20} className="text-[#3b506c]" />}
                                        </button>
                                    )
                                })}
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}