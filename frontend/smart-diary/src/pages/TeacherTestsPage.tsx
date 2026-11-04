import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from "../../@/components/ui/button.tsx";
import bgImage from '@/assets/bg.png';
import homeIcon from '@/assets/Home-Logo.svg';
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/Errors.ts';

interface UserProfile {
    full_name: string;
    subject?: {
        subject_id: number;
        name: string;
    };
}

interface DashboardClass {
    class_id: number;
    class_name: string;
}

interface DashboardTest {
    test_id: number;
    topic_id: number;
    topic_title: string;
    class_id: number;
    status: string;
    lesson_id?: string | null;
    title: string;
}

interface TeacherDashboardData {
    classes: DashboardClass[];
    tests: DashboardTest[];
}

interface JournalLesson {
    lesson_id: string;
    lesson_date: string;
    lesson_number?: number | null;
    topic_title?: string | null;
    homework?: string | null;
}

export default function TeacherTestsPage() {
    const navigate = useNavigate();
    const location = useLocation();
    
    const [user, setUser] = useState<UserProfile | null>(null);
    const [dashboard, setDashboard] = useState<TeacherDashboardData | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const [selectedTest, setSelectedTest] = useState<DashboardTest | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);

    const [publishMode, setPublishMode] = useState(false);
    const [lessons, setLessons] = useState<JournalLesson[]>([]);
    const [isLoadingLessons, setIsLoadingLessons] = useState(false);

    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    const showToast = (message: string, type: 'success' | 'error') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    const fetchData = async () => {
        try {
            const [userData, dashboardData] = await Promise.all([
                apiFetch<UserProfile>('/users/me'),
                apiFetch<TeacherDashboardData>('/teacher/dashboard')
            ]);
            setUser(userData);
            setDashboard(dashboardData);
        } catch (err) {
            console.error("Ошибка загрузки данных:", err);
            showToast(getErrorMessage(err), 'error');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [location.key]);

    const handleDelete = async () => {
        if (!selectedTest) return;
        setIsDeleting(true);

        try {
            await apiFetch(`/teacher/tests/${selectedTest.test_id}`, { method: 'DELETE' });
            showToast('Тест удалён', 'success');
            closeSheet();
            fetchData();
        } catch (err) {
            showToast(getErrorMessage(err), 'error');
        } finally {
            setIsDeleting(false);
        }
    };

    const openPublishMode = async () => {
        if (!selectedTest || !user?.subject?.subject_id) {
            showToast('Не удалось определить предмет', 'error');
            return;
        }

        setPublishMode(true);
        setIsLoadingLessons(true);
        setLessons([]);

        try {
            const data = await apiFetch<{ lessons: JournalLesson[] }>(
                `/classes/${selectedTest.class_id}/journal?subject_id=${user.subject.subject_id}&page=1&page_size=50`
            );
            const rawLessons = data.lessons || [];

            const sorted = [...rawLessons].sort((a, b) =>
                new Date(a.lesson_date).getTime() - new Date(b.lesson_date).getTime()
            );

            setLessons(sorted);
        } catch (err) {
            showToast(getErrorMessage(err), 'error');
        } finally {
            setIsLoadingLessons(false);
        }
    };

    const handlePublish = async (lesson: JournalLesson) => {
        if (!selectedTest) return;
        setIsPublishing(true);

        try {
            await apiFetch('/teacher/tests/publish', {
                method: 'POST',
                json: {
                    test_id: selectedTest.test_id,
                    lesson_id: lesson.lesson_id
                }
            });

            showToast('Тест опубликован!', 'success');
            closeSheet();
            fetchData();
        } catch (err) {
            showToast(getErrorMessage(err), 'error');
        } finally {
            setIsPublishing(false);
        }
    };

    const closeSheet = () => {
        setSelectedTest(null);
        setPublishMode(false);
        setLessons([]);
    };

    const formatLessonDate = (iso: string) => {
        try {
            const d = new Date(iso);
            return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
        } catch {
            return iso;
        }
    };

    const container = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    const item = {
        hidden: { opacity: 0, y: 30 },
        show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } }
    };

    const getTestColor = (index: number) => {
        const colors = [
            'bg-[#EBF1F1] text-[#596070]',
            'bg-[#B2CDE0] text-[#596070]',
            'bg-[#94A9BE] text-white'
        ];
        return colors[index % 3];
    };

    const groupedTests: Record<number, DashboardTest[]> = {};
    dashboard?.tests.forEach(test => {
        if (!groupedTests[test.class_id]) groupedTests[test.class_id] = [];
        groupedTests[test.class_id].push(test);
    });

    return (
        <div className="relative min-h-screen w-full bg-[#EAF1F1] overflow-x-hidden flex justify-center pb-10">
            <div
                className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0"
                style={{ backgroundImage: `url(${bgImage})` }}
            />

            <AnimatePresence>
                {toast && (
                    <motion.div
                        initial={{ opacity: 0, y: -50 }}
                        animate={{ opacity: 1, y: 20 }}
                        exit={{ opacity: 0, y: -50 }}
                        className={`fixed top-0 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-full shadow-lg backdrop-blur-md border ${
                            toast.type === 'success'
                                ? 'bg-white/90 border-green-200 text-[#596070]'
                                : 'bg-white/90 border-red-200 text-red-600'
                        }`}
                    >
                        <span className="font-bold text-sm">{toast.message}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="relative z-10 w-full max-w-[440px] mx-auto flex flex-col px-4"
            >
                <motion.header
                    variants={item}
                    className="bg-[#B2CDE0] px-4 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between mt-2"
                >
                    <button onClick={() => navigate('/teacher')} className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors shrink-0">
                        <img src={homeIcon} alt="Home" className="w-full h-full object-contain" />
                    </button>

                    <div className="flex flex-col items-center text-center px-2 flex-1 min-w-0">
                        <h2 className="text-white font-bold text-[14px] leading-tight max-w-full truncate">
                            {isLoading ? "Загрузка..." : user?.full_name}
                        </h2>
                        <p className="text-white/80 text-[11px] font-medium mt-0.5 truncate w-full">
                            {isLoading ? "..." : user?.subject?.name ? `Учитель ${user.subject.name.toLowerCase()}` : "Учитель"}
                        </p>
                    </div>

                    <div className="w-12 h-12 shrink-0" />
                </motion.header>

                <motion.div variants={item} className="text-center mt-8 w-full">
                    <h1 className="text-[32px] font-extrabold text-[#596070]">Тесты</h1>
                </motion.div>

                {isLoading ? (
                    <div className="flex-1 flex items-center justify-center font-bold text-[#596070] mt-20">Загрузка тестов...</div>
                ) : !dashboard || Object.keys(groupedTests).length === 0 ? (
                    <motion.div variants={item} className="mt-10 text-center w-full">
                        <div className="bg-white/60 backdrop-blur-md rounded-[40px] p-8 shadow-sm border border-white/50">
                            <h2 className="text-[20px] font-bold text-[#596070] mb-2">У вас пока нет тестов</h2>
                            <p className="text-[#859bb1] text-sm font-bold mb-6">Создайте первый тест с помощью ИИ или вручную.</p>
                        </div>
                    </motion.div>
                ) : (
                    <motion.div variants={item} className="mt-6 flex flex-col gap-8 w-full">
                        {Object.entries(groupedTests).map(([classId, tests]) => {
                            const classInfo = dashboard.classes.find(c => c.class_id === Number(classId));
                            const className = classInfo ? classInfo.class_name : `Класс ${classId}`;

                            return (
                                <div key={classId} className="flex flex-col w-full">
                                    <h3 className="text-[20px] font-extrabold text-[#596070] mb-3 px-1">
                                        {className} КЛАСС
                                    </h3>

                                    <div className="grid grid-cols-3 gap-3 w-full">
                                        {tests.map((test, index) => (
                                            <motion.button
                                                key={test.test_id}
                                                whileHover={{ scale: 1.05 }}
                                                whileTap={{ scale: 0.95 }}
                                                onClick={() => {
                                                    setSelectedTest(test);
                                                    setPublishMode(false);
                                                }}
                                                className={`relative aspect-square w-full min-w-0 rounded-[20px] p-2 flex flex-col items-center justify-center text-center shadow-sm font-bold text-[13px] leading-tight transition-colors ${getTestColor(index)}`}
                                            >
                                                <span
                                                    className={`absolute top-2 right-2 w-2.5 h-2.5 rounded-full border-[1.5px] ${
                                                        test.status === 'draft'
                                                            ? 'border-[#859bb1] bg-transparent'
                                                            : 'border-[#596070] bg-[#596070]'
                                                    }`}
                                                />
                                                <span className="line-clamp-3 w-full break-words overflow-hidden px-1">
                                                    {test.title}
                                                </span>
                                            </motion.button>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </motion.div>
                )}

                <motion.div variants={item} className="mt-10 flex flex-col gap-4 w-full">
                    <Button
                        onClick={() => navigate('/teacher/tests/create')}
                        className="w-full h-[60px] bg-white/70 backdrop-blur-md rounded-full shadow-sm text-[#596070] text-[18px] font-extrabold hover:bg-white transition-all shrink-0"
                    >
                        Создать новый тест
                    </Button>
                </motion.div>
            </motion.div>

            <AnimatePresence>
                {selectedTest && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end justify-center"
                        onClick={closeSheet}
                    >
                        <motion.div
                            initial={{ y: '100%' }}
                            animate={{ y: 0 }}
                            exit={{ y: '100%' }}
                            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                            onClick={e => e.stopPropagation()}
                            className="bg-white rounded-t-[40px] p-6 w-full max-w-[440px] shadow-2xl pb-10 max-h-[85vh] overflow-y-auto"
                        >
                            <div className="w-12 h-1.5 bg-gray-300 rounded-full mx-auto mb-6" />

                            {!publishMode ? (
                                <>
                                    <h3 className="text-xl font-extrabold text-[#596070] text-center mb-1">
                                        {selectedTest.topic_title}
                                    </h3>
                                    <p className="text-center text-[#859bb1] font-bold text-xs mb-6">
                                        Статус: {selectedTest.status === 'draft' ? 'черновик' : 'опубликован'}
                                    </p>

                                    <div className="flex flex-col gap-3">
                                        {selectedTest.status === 'draft' && (
                                            <Button
                                                onClick={() => navigate(`/teacher/tests/edit/${selectedTest.test_id}`)}
                                                className="w-full h-[60px] bg-[#94A9BE] hover:bg-[#859bb1] text-white rounded-full text-[18px] font-extrabold"
                                            >
                                                Редактировать тест
                                            </Button>
                                        )}

                                        {selectedTest.status === 'draft' && (
                                            <Button
                                                onClick={openPublishMode}
                                                className="w-full h-[60px] bg-[#7FB280] hover:bg-[#6fa070] text-white rounded-full text-[18px] font-extrabold"
                                            >
                                                Опубликовать тест
                                            </Button>
                                        )}

                                        <Button
                                            onClick={handleDelete}
                                            disabled={isDeleting}
                                            className="w-full h-[60px] bg-[#D48B8B] hover:bg-[#c47a7a] text-white rounded-full text-[18px] font-extrabold disabled:opacity-50"
                                        >
                                            {isDeleting ? 'Удаление...' : 'Удалить тест'}
                                        </Button>

                                        <Button
                                            onClick={closeSheet}
                                            className="w-full h-[50px] bg-gray-100 hover:bg-gray-200 text-[#596070] rounded-full text-[16px] font-extrabold mt-2"
                                        >
                                            Отмена
                                        </Button>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="flex items-center justify-between mb-6">
                                        <button
                                            onClick={() => setPublishMode(false)}
                                            className="text-[#94A9BE] font-bold text-sm"
                                        >
                                            ← Назад
                                        </button>
                                        <h3 className="text-lg font-extrabold text-[#596070]">
                                            Выберите урок
                                        </h3>
                                        <div className="w-14" />
                                    </div>

                                    {isLoadingLessons ? (
                                        <div className="flex justify-center py-10">
                                            <div className="w-8 h-8 border-4 border-[#94A9BE] border-t-transparent rounded-full animate-spin" />
                                        </div>
                                    ) : lessons.length === 0 ? (
                                        <div className="text-center py-10 text-[#859bb1] font-bold">
                                            Нет доступных уроков для этого класса
                                        </div>
                                    ) : (
                                        <div className="flex flex-col gap-2 max-h-[60vh] overflow-y-auto">
                                            {lessons.map(lesson => (
                                                <button
                                                    key={lesson.lesson_id}
                                                    onClick={() => handlePublish(lesson)}
                                                    disabled={isPublishing}
                                                    className="text-left w-full bg-[#F4F8F8] hover:bg-[#e8f0f0] rounded-2xl p-4 transition-colors disabled:opacity-50"
                                                >
                                                    <div className="flex items-center justify-between mb-1">
                                                        <span className="font-extrabold text-[#596070] text-sm">
                                                            {formatLessonDate(lesson.lesson_date)}
                                                            {lesson.lesson_number ? `, ${lesson.lesson_number} урок` : ''}
                                                        </span>
                                                        <span className="text-[#94A9BE] font-bold text-xs">→</span>
                                                    </div>
                                                    <p className="text-[#596070] font-bold text-sm leading-tight">
                                                        {lesson.topic_title || 'Без темы'}
                                                    </p>
                                                </button>
                                            ))}
                                        </div>
                                    )}

                                    {isPublishing && (
                                        <p className="text-center text-[#859bb1] font-bold text-sm mt-4">
                                            Публикация...
                                        </p>
                                    )}
                                </>
                            )}
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}