import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import bgImage from '@/assets/bg.png';
import homeIcon from '@/assets/Home-Logo.svg';
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/Errors';

interface Student { student_id: number; full_name: string; }
interface Grade { student_id: number; value: number; }
interface Lesson { lesson_id: string; lesson_date: string; topic_title: string | null; grades: Grade[]; }
interface JournalData { students: Student[]; lessons: Lesson[]; page: number; total_pages: number; }
interface UserProfile { full_name: string; subject?: { subject_id: number; name: string; }; }

export default function JournalPage() {
    const { classId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();

    const displayClassName = location.state?.className
        ? `${location.state.className} КЛАСС`
        : `${classId} КЛАСС`;

    const [user, setUser] = useState<UserProfile | null>(null);
    const [data, setData] = useState<JournalData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    useEffect(() => {
        const fetchJournalData = async () => {
            setIsLoading(true);
            setErrorMsg(null);

            try {
                const userData = await apiFetch<UserProfile>('/users/me');
                setUser(userData);

                if (!userData.subject) {
                    setErrorMsg("В вашем профиле не указан предмет. Журнал недоступен.");
                    setIsLoading(false);
                    return;
                }

                const journalData = await apiFetch<JournalData>(
                    `/classes/${classId}/journal?subject_id=${userData.subject.subject_id}&page=${page}&page_size=10`
                );
                setData(journalData);
            } catch (err) {
                setErrorMsg(getErrorMessage(err));
            } finally {
                setIsLoading(false);
            }
        };

        fetchJournalData();
    }, [classId, page]);

    const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
    const item = { hidden: { opacity: 0, y: 30 }, show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } } };

    const formatDate = (dateString: string) => {
        if (!dateString) return '';
        const parts = dateString.split('-');
        return parts.length === 3 ? `${parts[2]}.${parts[1]}` : dateString;
    };

    const handleDragEnd = (_e: any, info: { offset: { x: number } }) => {
        if (!data) return;
        const swipeThreshold = 80;
        const swipe = info.offset.x;

        if (swipe < -swipeThreshold && page < data.total_pages) {
            setPage(p => p + 1);
        } else if (swipe > swipeThreshold && page > 1) {
            setPage(p => p - 1);
        }
    };

    const getGradeColor = (value: number) => {
        if (value === 5) return 'bg-[#596070] text-white';
        if (value === 4) return 'bg-[#94A9BE] text-white';
        if (value === 3) return 'bg-[#B2CDE0] text-[#596070]';
        return 'bg-[#D48B8B] text-white';
    };

    return (
        <div className="relative min-h-screen bg-[#F4F8F8] overflow-x-hidden flex flex-col items-center pb-4">
            <div className="fixed inset-0 bg-cover bg-center opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <motion.div variants={container} initial="hidden" animate="show" className="relative z-10 w-full max-w-[440px] flex flex-col flex-1">
                <motion.header variants={item} className="bg-[#B2CDE0] px-6 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between shrink-0 z-20">
                    <button onClick={() => navigate(`/teacher/classes/${classId}`, { state: location.state })} className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors">
                        <img src={homeIcon} alt="Home" className="w-full h-full object-contain" />
                    </button>
                    <h1 className="text-[24px] font-extrabold text-[#596070] tracking-wide">{displayClassName}</h1>
                    <div className="w-12 h-12" />
                </motion.header>

                <motion.div variants={item} className="text-center mt-4 shrink-0 z-20">
                    <h2 className="text-[28px] font-extrabold text-[#596070]">Журнал</h2>
                    <p className="text-[#859bb1] font-bold text-sm">
                        {user?.subject?.name || 'Загрузка...'}
                    </p>
                </motion.div>

                {isLoading ? (
                    <div className="flex-1 flex flex-col items-center justify-center font-bold text-[#596070]">
                        <div className="w-8 h-8 border-4 border-[#94A9BE] border-t-transparent rounded-full animate-spin mb-4"></div>
                        Загрузка...
                    </div>
                ) : errorMsg ? (
                    <div className="flex-1 flex items-center justify-center font-bold text-[#D48B8B] px-6 text-center">
                        {errorMsg}
                    </div>
                ) : !data || data.lessons.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center font-bold text-[#596070] px-6 text-center">
                        В журнале пока нет уроков и оценок
                    </div>
                ) : (
                    <motion.div variants={item} className="mt-4 px-4 flex flex-col">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={page}
                                initial={{ opacity: 0, x: 50 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -50 }}
                                transition={{ duration: 0.3 }}
                                drag="x"
                                dragConstraints={{ left: 0, right: 0 }}
                                dragElastic={0.2}
                                onDragEnd={handleDragEnd}
                                className="bg-white/80 backdrop-blur-md rounded-[30px] shadow-[0px_10px_30px_rgba(0,0,0,0.05)] border border-white/50 overflow-x-auto pb-2 cursor-grab active:cursor-grabbing [&::-webkit-scrollbar]:hidden"
                            >
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                    <tr>
                                        <th className="sticky left-0 bg-[#F4F8F8]/95 backdrop-blur-md p-3 text-[12px] font-extrabold text-[#596070] border-b border-[#C9D9E6] min-w-[130px] z-20 align-bottom h-40">
                                            Ученик
                                        </th>
                                        {data.lessons.map(lesson => (
                                            <th key={lesson.lesson_id} className="p-0 border-b border-[#C9D9E6] text-center min-w-[64px] h-40 align-bottom">
                                                <div className="[writing-mode:vertical-rl] rotate-180 flex items-start justify-start h-full py-2 px-1 mx-auto w-full">
                                                        <span className="font-extrabold text-[12px] text-[#596070] shrink-0">
                                                            {formatDate(lesson.lesson_date)}
                                                        </span>
                                                    {lesson.topic_title && (
                                                        <span className="text-[10px] font-bold text-[#859bb1] mt-2 opacity-80 leading-tight whitespace-normal break-words">
                                                                {lesson.topic_title}
                                                            </span>
                                                    )}
                                                </div>
                                            </th>
                                        ))}
                                    </tr>
                                    </thead>
                                    <tbody>
                                    {data.students.map((student, idx) => (
                                        <tr key={student.student_id} className={idx % 2 === 0 ? 'bg-white/50' : 'bg-transparent'}>
                                            <td className="sticky left-0 bg-[#F4F8F8]/95 backdrop-blur-md p-3 text-[11px] font-bold text-[#596070] border-b border-[#C9D9E6] z-10 truncate max-w-[130px]">
                                                {student.full_name.split(' ')[0]}<br/>
                                                <span className="text-[10px] text-[#859bb1]">{student.full_name.split(' ')[1]?.charAt(0)}. {student.full_name.split(' ')[2]?.charAt(0)}.</span>
                                            </td>
                                            {data.lessons.map(lesson => {
                                                const grade = lesson.grades.find(g => g.student_id === student.student_id);
                                                return (
                                                    <td key={lesson.lesson_id} className="p-2 text-center border-b border-[#C9D9E6]">
                                                        {grade ? (
                                                            <span className={`inline-flex items-center justify-center w-7 h-7 rounded-lg font-extrabold text-[13px] shadow-sm ${getGradeColor(grade.value)}`}>
                                                                    {grade.value}
                                                                </span>
                                                        ) : (
                                                            <span className="text-[#C9D9E6] text-lg font-bold">·</span>
                                                        )}
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    ))}
                                    </tbody>
                                </table>
                            </motion.div>
                        </AnimatePresence>

                        {data.total_pages > 1 && (
                            <div className="flex items-center justify-center gap-2 mt-4 pb-4">
                                {Array.from({ length: data.total_pages }).map((_, i) => (
                                    <div
                                        key={i}
                                        className={`h-2 rounded-full transition-all duration-300 ${
                                            page === i + 1 ? 'w-6 bg-[#94A9BE]' : 'w-2 bg-[#C9D9E6]'
                                        }`}
                                    />
                                ))}
                            </div>
                        )}
                    </motion.div>
                )}
            </motion.div>
        </div>
    );
}