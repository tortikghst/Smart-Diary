import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ChevronRight, ChevronLeft } from "lucide-react";
import { Button } from "../../@/components/ui/button";
import { Card, CardContent } from "../../@/components/ui/card";
import bgImage from '../assets/bg.png';

// --- ИНТЕРФЕЙСЫ ПО СВАГГЕРУ ---

interface UserProfile {
    full_name: string;
    class_name: string;
}

interface DashboardData {
    subjects: { subject_id: number; name: string }[];
    streak: { current_streak: number };
    debts_count: number;
    available_tests: {
        test_id: number;
        topic_title: string;
        subject_name: string;
        attempts_used: number;
        attempts_left: number;
        best_percent: number;
    }[];
}

interface GradeData {
    subject: { subject_id: number; name: string };
    avg_score: number | null;
    homework_percent: number;
    grades: {
        grade_id: number;
        value: number;
        lesson_date: string;
        topic_title: string | null;
        work_type: string;
    }[];
}

interface RatingData {
    type: string;
    items: {
        place: number;
        class_id: number;
        class_name: string;
        avg_score: number;
    }[];
    my_class_id: number;
}

export default function StudentDashboard() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [dashboard, setDashboard] = useState<DashboardData | null>(null);
    const [rating, setRating] = useState<RatingData | null>(null);

    const [currentGrades, setCurrentGrades] = useState<GradeData | null>(null);
    const [activeSubjectIndex, setActiveSubjectIndex] = useState(0);

    const [isLoading, setIsLoading] = useState(true);
    const [isGradesLoading, setIsGradesLoading] = useState(false);
    const [selectedGrade, setSelectedGrade] = useState<{ subject: string; grade: number; date: string; topic: string } | null>(null);

    const navigate = useNavigate();

    useEffect(() => {
        const fetchInitialData = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
                setIsLoading(false);
                return;
            }

            const headers = { 'Authorization': `Bearer ${token}` };

            try {
                const [userRes, dashRes, ratingRes] = await Promise.all([
                    fetch('/api/v1/users/me', { headers }),
                    fetch('/api/v1/student/dashboard', { headers }),
                    fetch('/api/v1/student/rating?type=vpr', { headers })
                ]);

                if (userRes.ok) setUser(await userRes.json());
                if (dashRes.ok) setDashboard(await dashRes.json());
                if (ratingRes.ok) setRating(await ratingRes.json());

            } catch (err) {
                console.error("Ошибка API:", err);
            } finally {
                setIsLoading(false);
            }
        };

        fetchInitialData();
    }, [navigate]);

    useEffect(() => {
        if (!dashboard?.subjects || dashboard.subjects.length === 0) return;

        const fetchGrades = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) return;

            setIsGradesLoading(true);
            const subjectId = dashboard.subjects[activeSubjectIndex].subject_id;

            try {
                const res = await fetch(`/api/v1/student/grades?subject_id=${subjectId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    setCurrentGrades(await res.json());
                }
            } catch (err) {
                console.error("Ошибка загрузки оценок:", err);
            } finally {
                setIsGradesLoading(false);
            }
        };

        fetchGrades();
    }, [dashboard?.subjects, activeSubjectIndex]);

    const getDebtsText = (count: number) => {
        if (count === 0) return "У вас сейчас нет задолженностей.";
        const lastDigit = count % 10;
        const lastTwo = count % 100;
        if (lastDigit === 1 && lastTwo !== 11) return `У вас ${count} задолженность.`;
        if ([2, 3, 4].includes(lastDigit) && ![12, 13, 14].includes(lastTwo)) return `У вас ${count} задолженности.`;
        return `У вас ${count} задолженностей.`;
    };

    const getTestsText = (count: number) => {
        const lastDigit = count % 10;
        const lastTwo = count % 100;
        if (lastDigit === 1 && lastTwo !== 11) return `${count} тест`;
        if ([2, 3, 4].includes(lastDigit) && ![12, 13, 14].includes(lastTwo)) return `${count} теста`;
        return `${count} тестов`;
    };

    const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
    const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } } };

    const totalSubjects = dashboard?.subjects?.length || 1;
    const canPrev = activeSubjectIndex > 0;
    const canNext = activeSubjectIndex < totalSubjects - 1;

    if (isLoading) {
        return <div className="min-h-screen flex items-center justify-center bg-[#f2f6f9] text-[#3b506c] font-bold">Загрузка...</div>;
    }

    // --- ЛОГИКА ДЛЯ ТОПА КЛАССОВ ---
    const top3 = rating?.items?.slice(0, 3) || [];
    const myClass = rating?.items?.find(c => c.class_id === rating?.my_class_id);

    let displayClasses = [...top3];
    // Если класса ученика нет в топ-3, добавляем его
    if (myClass && !top3.some(c => c.class_id === myClass.class_id)) {
        displayClasses.push(myClass);
    }

    const maxScore = Math.max(...displayClasses.map(c => c.avg_score), 5);

    const sortedGrades = [...(currentGrades?.grades || [])].sort((a, b) => new Date(a.lesson_date).getTime() - new Date(b.lesson_date).getTime());
    const uniqueDates = Array.from(new Set(sortedGrades.map(g => g.lesson_date)));
    const uniqueTopics = Array.from(new Set(sortedGrades.map(g => g.topic_title || 'Без темы'))).slice(-7);

    const formatDate = (dateString: string) => {
        if (!dateString) return '';
        const parts = dateString.split('-');
        return parts.length === 3 ? `${parts[2]}.${parts[1]}` : dateString;
    };

    return (
        <div className="relative min-h-screen bg-[#f2f6f9] overflow-x-hidden flex justify-center font-sans">
            <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <motion.div variants={container} initial="hidden" animate="show" className="relative z-10 w-full max-w-[430px] flex flex-col gap-4 pb-10">

                {/* Шапка */}
                <motion.header variants={item} className="bg-[#B2CDE0] px-5 py-4 rounded-b-[40px] shadow-sm flex justify-between items-center min-h-[90px]">
                    <div className="text-[#3b506c]">
                        <h2 className="text-[17px] font-extrabold leading-tight">{user?.full_name || "Ученик"}</h2>
                        <p className="text-[14px] font-semibold text-[#556b86] mt-1">Ученик {user?.class_name} класса</p>
                    </div>

                    {/* Огонек в шапке */}
                    <motion.button
                        whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                        onClick={() => navigate('/student/mascot')}
                        className="relative w-[60px] h-[56px] flex items-center justify-center cursor-pointer"
                    >
                        <svg viewBox="0 0 70 64" className="absolute inset-0 w-full h-full pointer-events-none" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect width="70" height="64" x="0" y="0" />
                            <path d="M10.1047 54.7613C14.3761 58.6666 21.2507 58.6666 35 58.6666C48.7492 58.6666 55.624 58.6666 59.8952 54.7613C64.1667 50.8562 64.1667 44.5706 64.1667 32C64.1667 19.4292 64.1667 13.1438 59.8952 9.23857C55.624 5.33331 48.7492 5.33331 35 5.33331C21.2507 5.33331 14.3761 5.33331 10.1047 9.23857C5.83334 13.1438 5.83334 19.4292 5.83334 32C5.83334 44.5706 5.83334 50.8562 10.1047 54.7613Z" fill="#94A9BE" />
                            <path d="M55.1515 32.9859C55.1515 48.8759 40.8214 52.8485 33.6567 52.8485C27.3872 52.8485 14.8485 48.8759 14.8485 32.9859C14.8485 26.075 19.1324 21.6872 22.7315 19.4787C24.377 18.469 26.4236 19.1143 26.5299 20.9369C26.7627 24.9246 30.0887 28.1281 32.6644 24.9212C35.0218 21.9859 36.1853 18.0001 36.1853 15.6065C36.1853 12.0805 40.0479 9.83991 43.0638 12.0002C48.942 16.2109 55.1515 23.2629 55.1515 32.9859Z" fill="#1c274c" />
                        </svg>
                        <span className="relative z-10 text-white text-[20px] font-black pb-1 pointer-events-none mt-1">
                            {dashboard?.streak?.current_streak || 0}
                        </span>
                    </motion.button>
                </motion.header>

                <motion.div variants={item} className="text-center my-1">
                    <h1 className="text-[32px] font-extrabold text-[#3b506c]">Главная</h1>
                </motion.div>

                {/* Карточка Оценок */}
                <motion.div variants={item}>
                    <Card className="bg-white/80 backdrop-blur-md mx-4 rounded-[30px] shadow-sm border-none overflow-hidden relative">
                        <CardContent className="p-5">
                            <div className="flex justify-between items-center text-[18px] font-extrabold text-[#3b506c] mb-3 px-2">
                                <button
                                    onClick={() => canPrev && setActiveSubjectIndex(prev => prev - 1)}
                                    disabled={!canPrev}
                                    className={`${!canPrev ? 'text-gray-300' : 'text-[#94A9BE] hover:text-[#3b506c]'} transition-colors`}
                                >
                                    <ChevronLeft size={24}/>
                                </button>
                                <span>{dashboard?.subjects?.[activeSubjectIndex]?.name || "Нет предметов"}</span>
                                <button
                                    onClick={() => canNext && setActiveSubjectIndex(prev => prev + 1)}
                                    disabled={!canNext}
                                    className={`${!canNext ? 'text-gray-300' : 'text-[#94A9BE] hover:text-[#3b506c]'} transition-colors`}
                                >
                                    <ChevronRight size={24}/>
                                </button>
                            </div>

                            {!isGradesLoading && currentGrades && (
                                <div className="flex justify-around items-center mb-4 py-2 bg-[#f7fafc] rounded-2xl">
                                    <div className="text-center flex-1">
                                        <div className="text-[9px] font-bold text-[#94A9BE] uppercase tracking-wide">Средний балл</div>
                                        <div className="text-[18px] font-extrabold text-[#3b506c]">
                                            {currentGrades.avg_score != null ? currentGrades.avg_score.toFixed(1) : '—'}
                                        </div>
                                    </div>
                                    <div className="w-px h-8 bg-[#dde5ed]" />
                                    <div className="text-center flex-1">
                                        <div className="text-[9px] font-bold text-[#94A9BE] uppercase tracking-wide">Успеваемость ДЗ</div>
                                        <div className="text-[18px] font-extrabold text-[#3b506c]">
                                            {currentGrades.homework_percent}%
                                        </div>
                                    </div>
                                </div>
                            )}

                            {isGradesLoading ? (
                                <div className="flex justify-center items-center h-[200px] text-[#3b506c] animate-pulse">Загрузка оценок...</div>
                            ) : sortedGrades.length > 0 ? (
                                <div className="bg-white rounded-[20px] shadow-sm border border-gray-100 overflow-hidden">
                                    <div className="max-h-[240px] overflow-auto [&::-webkit-scrollbar]:hidden relative">
                                        <table className="w-full text-left border-collapse min-w-max">
                                            <thead>
                                            <tr>
                                                <th className="sticky top-0 left-0 bg-white p-2 text-[10px] font-extrabold text-[#94A9BE] border-b border-r border-gray-100 min-w-[100px] z-40">
                                                    Тема
                                                </th>
                                                {uniqueDates.map((date) => (
                                                    <th key={date} className="sticky top-0 bg-white p-2 text-[10px] font-bold text-[#3b506c] border-b border-gray-100 text-center min-w-[40px] z-30">
                                                        {formatDate(date)}
                                                    </th>
                                                ))}
                                            </tr>
                                            </thead>
                                            <tbody>
                                            {uniqueTopics.map((topic, idx) => (
                                                <tr key={topic} className={idx % 2 === 0 ? 'bg-transparent' : 'bg-gray-50/50'}>
                                                    <td className="sticky left-0 bg-white p-2 text-[10px] font-bold text-[#3b506c] border-b border-r border-gray-100 z-20 truncate max-w-[100px]">
                                                        {topic}
                                                    </td>
                                                    {uniqueDates.map((date) => {
                                                        const cellGrades = sortedGrades.filter(g => (g.topic_title || 'Без темы') === topic && g.lesson_date === date);
                                                        return (
                                                            <td key={date} className="p-1 border-b border-gray-100 text-center">
                                                                {cellGrades.length > 0 ? (
                                                                    <motion.button
                                                                        whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
                                                                        onClick={() => setSelectedGrade({
                                                                            subject: currentGrades?.subject.name || 'Предмет',
                                                                            grade: cellGrades[0].value,
                                                                            date: date,
                                                                            topic: topic
                                                                        })}
                                                                        className="w-7 h-7 mx-auto rounded-lg bg-[#B2CDE0] text-white font-extrabold text-[12px] flex items-center justify-center shadow-sm"
                                                                    >
                                                                        {cellGrades.map(g => g.value).join(' ')}
                                                                    </motion.button>
                                                                ) : (
                                                                    <span className="text-gray-200 text-xs">·</span>
                                                                )}
                                                            </td>
                                                        );
                                                    })}
                                                </tr>
                                            ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex justify-center items-center h-[100px] text-[#556b86] font-semibold">Оценок пока нет</div>
                            )}
                        </CardContent>
                    </Card>
                </motion.div>

                {/* Задолженности */}
                <motion.div variants={item}>
                    <motion.div
                        whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                        onClick={() => navigate('/student/debts')}
                        className="bg-white/80 backdrop-blur-md mx-4 p-5 rounded-[30px] shadow-sm cursor-pointer flex justify-between items-center relative"
                    >
                        <p className={`text-[16px] font-extrabold text-left underline decoration-[#3b506c] decoration-2 underline-offset-4 pr-6 text-[#3b506c]`}>
                            {getDebtsText(dashboard?.debts_count || 0)}
                        </p>
                        <ChevronRight className="w-5 h-5 text-[#B2CDE0] flex-shrink-0" />
                    </motion.div>
                </motion.div>

                {/* Лидеры (с классом ученика) */}
                <motion.div variants={item}>
                    <Card className="bg-white/80 backdrop-blur-md mx-4 rounded-[30px] shadow-sm border-none overflow-hidden">
                        <CardContent className="p-5 pb-0">
                            <div className="text-center text-[18px] font-extrabold text-[#3b506c] mb-1">Лидеры по классам</div>
                            <div className="flex justify-center items-center gap-3 text-[14px] font-bold text-[#3b506c] mb-6">
                                <span>←</span> ВПР <span>→</span>
                            </div>

                            <div className="flex justify-center items-end gap-2 h-[160px] pb-6">
                                {displayClasses.length > 0 ? displayClasses.map((cls, index) => {
                                    const heightPx = Math.max(50, (cls.avg_score / maxScore) * 130);
                                    const isMyClass = cls.class_id === rating?.my_class_id;

                                    // Определяем цвета
                                    let colorClass = 'bg-[#EBF1F1] text-[#5f7a93]';
                                    if (isMyClass && index >= 3) {
                                        // Если мой класс добавлен вне топ-3
                                        colorClass = 'bg-[#1c274c] text-white shadow-md';
                                    } else if (index === 0) {
                                        colorClass = 'bg-[#94A9BE] text-white';
                                    } else if (index === 1) {
                                        colorClass = 'bg-[#B2CDE0] text-[#5f7a93]';
                                    } else if (index === 2) {
                                        colorClass = 'bg-[#D6E4F0] text-[#5f7a93]';
                                    }

                                    return (
                                        <motion.div
                                            key={cls.class_id}
                                            initial={{ height: 0 }}
                                            animate={{ height: `${heightPx}px` }}
                                            transition={{ delay: 0.3 + (index * 0.1), duration: 0.8, type: "spring" }}
                                            className={`w-[60px] ${colorClass} rounded-[20px] flex flex-col justify-start items-center pt-3 shadow-sm relative`}
                                        >
                                            <span className="text-[16px] font-extrabold">{cls.class_name}</span>
                                            {isMyClass && (
                                                <span className="text-[9px] font-bold mt-1 opacity-80">(Мой)</span>
                                            )}
                                        </motion.div>
                                    )
                                }) : (
                                    <div className="text-[#556b86] font-semibold mb-10">Нет данных</div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>

                {/* Тесты */}
                <motion.div variants={item}>
                    <Card className="bg-white/80 backdrop-blur-md mx-4 rounded-[30px] shadow-sm border-none text-center">
                        <CardContent className="p-6">
                            <div className="text-[18px] font-extrabold text-[#3b506c] mb-2">Тесты</div>
                            <p className="text-[14px] font-bold text-[#3b506c] mb-5 leading-snug">
                                В данный момент доступно<br/>{getTestsText(dashboard?.available_tests?.length || 0)}.
                            </p>
                            <Button
                                className="w-full h-12 bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] font-extrabold text-[16px] rounded-[20px] transition-all"
                                onClick={() => navigate('/student/tests')}
                            >
                                Выполнить
                            </Button>
                        </CardContent>
                    </Card>
                </motion.div>

            </motion.div>

            {/* Модалка с подробностями оценки */}
            <AnimatePresence>
                {selectedGrade && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm px-4"
                        onClick={() => setSelectedGrade(null)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, y: 20 }}
                            className="bg-white rounded-[30px] p-6 w-full max-w-[320px] text-center shadow-xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="w-16 h-16 bg-[#f2f6f9] rounded-full flex items-center justify-center mx-auto mb-4">
                                <span className="text-3xl font-extrabold text-[#3b506c]">{selectedGrade.grade}</span>
                            </div>
                            <h3 className="text-lg font-extrabold text-[#3b506c] mb-1">{selectedGrade.subject}</h3>
                            <p className="text-sm font-semibold text-[#556b86] mb-4">Тема: {selectedGrade.topic}</p>
                            <p className="text-xs font-bold text-[#94A9BE] mb-6">Дата: {selectedGrade.date}</p>
                            <Button
                                onClick={() => setSelectedGrade(null)}
                                className="w-full bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] font-extrabold rounded-xl py-6"
                            >
                                Закрыть
                            </Button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}