import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import bgImage from '@/assets/bg.png';
import homeIcon from '@/assets/Home-Logo.svg';
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/Errors';

interface Student { student_id: number; full_name: string; }
interface Grade { student_id: number; value: number | string; }
interface Lesson { lesson_id: string; lesson_date: string; topic_title: string | null; grades: Grade[]; }
interface JournalData { students: Student[]; lessons: Lesson[]; page: number; total_pages: number; }
interface UserProfile { full_name: string; subject?: { subject_id: number; name: string; }; }

// Тип для уведомлений
type ToastState = { message: string; type: 'success' | 'error' } | null;

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

    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isUploading, setIsUploading] = useState(false);
    
    // Состояние для красивого уведомления вместо alert
    const [toast, setToast] = useState<ToastState>(null);

    // Автоматическое скрытие уведомления через 4 секунды
    useEffect(() => {
        if (toast) {
            const timer = setTimeout(() => setToast(null), 4000);
            return () => clearTimeout(timer);
        }
    }, [toast]);

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

    useEffect(() => {
        fetchJournalData();
    }, [classId, page]);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            await apiFetch(`/teacher/journal/import`, {
                method: 'POST',
                body: formData,
            } as any);
            
            if (page === 1) {
                fetchJournalData();
            } else {
                setPage(1);
            }
            // Вместо alert показываем красивый тост
            setToast({ message: 'Журнал успешно загружен и обновлен!', type: 'success' });
        } catch (err) {
            setToast({ message: `Ошибка: ${getErrorMessage(err)}`, type: 'error' });
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
    const item = { hidden: { opacity: 0, y: 30 }, show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } } };

    const formatDate = (dateString: string) => {
        if (!dateString) return '';
        const dateOnly = dateString.split(' ')[0];
        const parts = dateOnly.split('-');
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

    const getGradeColor = (value: number | string) => {
        if (value === 5) return 'bg-[#596070] text-white';
        if (value === 4) return 'bg-[#94A9BE] text-white';
        if (value === 3) return 'bg-[#B2CDE0] text-[#596070]';
        return 'bg-[#D48B8B] text-white';
    };

    return (
        <div className="relative min-h-screen bg-[#F4F8F8] overflow-x-hidden flex flex-col items-center pb-4">
            <div className="fixed inset-0 bg-cover bg-center opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            {/* 👇 КРАСИВОЕ УВЕДОМЛЕНИЕ (TOAST) 👇 */}
            <AnimatePresence>
                {toast && (
                    <motion.div
                        initial={{ opacity: 0, y: -50, x: '-50%' }}
                        animate={{ opacity: 1, y: 20, x: '-50%' }}
                        exit={{ opacity: 0, y: -20, x: '-50%' }}
                        className={`fixed top-0 left-1/2 z-50 px-6 py-3 rounded-2xl shadow-xl border font-bold text-sm flex items-center gap-3 backdrop-blur-md max-w-[90vw] ${
                            toast.type === 'success' 
                            ? 'bg-[#596070]/95 text-white border-[#596070]' 
                            : 'bg-[#D48B8B]/95 text-white border-[#D48B8B]'
                        }`}
                    >
                        {toast.type === 'success' ? (
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        ) : (
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                        )}
                        <span className="flex-1">{toast.message}</span>
                    </motion.div>
                )}
            </AnimatePresence>
            {/* 👆 КОНЕЦ УВЕДОМЛЕНИЯ 👆 */}

            <motion.div variants={container} initial="hidden" animate="show" className="relative z-10 w-full max-w-[440px] flex flex-col flex-1">
                
                <motion.header variants={item} className="bg-[#B2CDE0] px-4 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between shrink-0 z-20">
                    <button onClick={() => navigate(`/teacher/classes/${classId}`, { state: location.state })} className="w-10 h-10 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors shrink-0">
                        <img src={homeIcon} alt="Home" className="w-full h-full object-contain" />
                    </button>
                    
                    <h1 className="text-[18px] font-extrabold text-[#596070] tracking-wide text-center truncate px-2">{displayClassName}</h1>
                    
                    <div className="shrink-0">
                        <input 
                            type="file" 
                            accept=".xlsx, .xls" 
                            className="hidden" 
                            ref={fileInputRef} 
                            onChange={handleFileUpload} 
                        />
                        <button 
                            onClick={() => fileInputRef.current?.click()} 
                            disabled={isUploading}
                            className="px-3 h-10 bg-[#596070] text-white rounded-xl flex items-center justify-center gap-1.5 hover:bg-[#4a5060] transition-colors disabled:opacity-50 shadow-md"
                            title="Загрузить Excel"
                        >
                            {isUploading ? (
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            ) : (
                                <>
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                        <polyline points="17 8 12 3 7 8"></polyline>
                                        <line x1="12" y1="3" x2="12" y2="15"></line>
                                    </svg>
                                    <span className="text-[11px] font-bold tracking-wide">Excel</span>
                                </>
                            )}
                        </button>
                    </div>
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
                    <div className="flex-1 flex items-center justify-center font-bold text-[#596070] px-6 text-center flex-col mt-10">
                        <p>В журнале пока нет уроков и оценок</p>
                        <button 
                            onClick={() => fileInputRef.current?.click()}
                            className="mt-4 bg-[#596070] text-white px-6 py-3 rounded-xl font-bold hover:bg-[#4a5060] transition-colors shadow-md flex items-center gap-2"
                        >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="17 8 12 3 7 8"></polyline>
                                <line x1="12" y1="3" x2="12" y2="15"></line>
                            </svg>
                            Загрузить Excel
                        </button>
                    </div>
                ) : (
                    <motion.div variants={item} className="mt-4 px-4 flex flex-col">
                        
                        <div className="text-center text-[11px] font-bold text-[#859bb1] mb-2">
                            ← Свайпните влево/вправо, чтобы посмотреть другие даты →
                        </div>

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
