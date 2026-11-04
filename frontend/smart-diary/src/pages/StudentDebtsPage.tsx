import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, BookOpen, AlertCircle } from 'lucide-react';
import { Button } from "../../@/components/ui/button";
import bgImage from '../assets/bg.png';
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/errors';

interface StudentDebt {
    debt_id: number;
    lesson_id: string;
    type: string;
    resolved: boolean;
    lesson_date: string;
    subject_name: string;
    topic_title: string;
}

export default function StudentDebtsPage() {
    const navigate = useNavigate();
    const [debts, setDebts] = useState<StudentDebt[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDebt, setSelectedDebt] = useState<StudentDebt | null>(null);
    const [isCreatingPrep, setIsCreatingPrep] = useState(false);
    
    // Стейт для ошибок
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    useEffect(() => {
        const fetchDebts = async () => {
            try {
                const data = await apiFetch<StudentDebt[]>('/student/debts');
                setDebts(data.filter((d) => !d.resolved));
            } catch (err) {
                console.error(err);
                // Можно добавить глобальный тост, если нужно
            } finally {
                setIsLoading(false);
            }
        };
        fetchDebts();
    }, []);

    const handleCreatePrepTest = async () => {
        if (!selectedDebt) return;
        setIsCreatingPrep(true);
        setErrorMsg(null); // Сбрасываем старую ошибку перед новым запросом

        try {
            const testData = await apiFetch<{ test_id: number, questions: any[] }>(
                `/student/debts/${selectedDebt.debt_id}/prep-test`, 
                { method: 'POST' }
            );

            if (!testData.questions || testData.questions.length === 0) {
                setErrorMsg("ИИ не сгенерировал ни одного вопроса. Попробуйте позже.");
                return;
            }

            navigate(`/student/tests/${testData.test_id}`, {
                state: { isPrep: true, preloadedTest: testData }
            });
        } catch (err) {
            setErrorMsg(getErrorMessage(err));
        } finally {
            setIsCreatingPrep(false);
        }
    };

    // Функция для закрытия панели со сбросом ошибки
    const closeSheet = () => {
        setSelectedDebt(null);
        setErrorMsg(null);
    };

    const formatDate = (dateString: string) => {
        if (!dateString) return '';
        const parts = dateString.split('-');
        return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : dateString;
    };

    return (
        <div className="relative min-h-screen bg-[#f2f6f9] overflow-x-hidden flex justify-center font-sans pb-10">
            <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <div className="relative z-10 w-full max-w-[430px] flex flex-col">
                {/* Шапка */}
                <header className="bg-[#B2CDE0] px-5 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between sticky top-0 z-20">
                    <button onClick={() => navigate('/student')} className="w-10 h-10 bg-[#94A9BE] rounded-xl flex items-center justify-center text-white hover:bg-[#859bb1] transition-colors">
                        <ChevronLeft size={24} />
                    </button>
                    <h1 className="text-[20px] font-extrabold text-[#3b506c]">Мои долги</h1>
                    <div className="w-10 h-10" />
                </header>

                <div className="mt-6 px-4">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-[200px] text-[#3b506c] animate-pulse font-bold">Загрузка...</div>
                    ) : debts.length === 0 ? (
                        <div className="bg-white/80 backdrop-blur-md rounded-[30px] p-8 text-center shadow-sm border border-white/50 mt-10">
                            <div className="w-20 h-20 bg-[#EBF1F1] rounded-full flex items-center justify-center mx-auto mb-4 text-[#94A9BE]">
                                <BookOpen size={40} />
                            </div>
                            <h2 className="text-[20px] font-extrabold text-[#3b506c] mb-2">У вас нет долгов</h2>
                            <p className="text-[#859bb1] text-sm font-bold">Все домашние задания сданы вовремя. Так держать!</p>
                        </div>
                    ) : (
                        <div className="flex flex-col gap-3">
                            {debts.map((debt) => (
                                <motion.div
                                    key={debt.debt_id}
                                    whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                    onClick={() => setSelectedDebt(debt)}
                                    className="bg-white/80 backdrop-blur-md rounded-[20px] p-4 shadow-sm border border-white/50 flex justify-between items-center cursor-pointer"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-[#f8e8e8] text-[#D48B8B] rounded-xl flex items-center justify-center shrink-0">
                                            <AlertCircle size={20} />
                                        </div>
                                        <div>
                                            <p className="text-[15px] font-extrabold text-[#3b506c] leading-tight line-clamp-1">{debt.topic_title}</p>
                                            <p className="text-[12px] font-bold text-[#859bb1] mt-0.5">{debt.subject_name} • {formatDate(debt.lesson_date)}</p>
                                        </div>
                                    </div>
                                    <ChevronRight className="text-[#B2CDE0] w-5 h-5 shrink-0" />
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Выпадающая панель с информацией о долге */}
            <AnimatePresence>
                {selectedDebt && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
                            onClick={closeSheet}
                        />
                        <motion.div
                            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
                            transition={{ type: "spring", damping: 25, stiffness: 200 }}
                            className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-[40px] p-6 pb-10 shadow-2xl flex flex-col items-center max-w-[430px] mx-auto"
                        >
                            <div className="w-12 h-1.5 bg-gray-200 rounded-full mb-6" />

                            <div className="w-16 h-16 bg-[#f8e8e8] text-[#D48B8B] rounded-full flex items-center justify-center mb-4">
                                <AlertCircle size={32} />
                            </div>

                            <h3 className="text-[20px] font-extrabold text-[#3b506c] text-center mb-1">{selectedDebt.topic_title}</h3>
                            <p className="text-[#859bb1] font-bold text-sm mb-6">{selectedDebt.subject_name} • {formatDate(selectedDebt.lesson_date)}</p>

                            <div className="w-full bg-[#f7fafc] rounded-2xl p-4 mb-6">
                                <p className="text-[13px] font-bold text-[#556b86] text-center leading-snug">
                                    Чтобы закрыть долг, предлагаем пройти короткий тренировочный тест по этой теме. ИИ сгенерирует вопросы специально для вас.
                                </p>
                            </div>

                            {/* Блок ошибки (вставляем строго перед кнопкой!) */}
                            {errorMsg && (
                                <div className="w-full bg-[#f8e8e8] border border-[#D48B8B]/30 text-[#D48B8B] p-3 rounded-xl mb-4 text-center text-[13px] font-bold leading-tight">
                                    {errorMsg}
                                </div>
                            )}

                            <Button
                                onClick={handleCreatePrepTest}
                                disabled={isCreatingPrep}
                                className="w-full h-14 bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] font-extrabold text-[16px] rounded-full shadow-md transition-all mb-3"
                            >
                                {isCreatingPrep ? 'Создание теста...' : 'Пройти тест для подготовки'}
                            </Button>

                            <Button
                                onClick={closeSheet}
                                className="w-full h-12 bg-transparent text-[#859bb1] font-bold text-[15px] rounded-full hover:bg-gray-50 transition-all"
                            >
                                Закрыть
                            </Button>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}