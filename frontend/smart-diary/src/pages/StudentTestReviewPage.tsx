import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, CheckCircle2, XCircle, Lightbulb, Trophy } from 'lucide-react';
import { Button } from "../../@/components/ui/button";
import bgImage from '../assets/bg.png';

interface AIFeedbackItem {
    question_id: number;
    question: string;
    your_answer: string;
    correct_answer: string;
    explanation?: string | null;
    image_url?: string | null;
}

interface AIFeedbackData {
    attempt_id: number;
    items: AIFeedbackItem[];
}

// ============================================================
// ФУНКЦИЯ ДЛЯ КРАСИВОГО ОТОБРАЖЕНИЯ MATCHING И МАССИВОВ
// ============================================================
const formatAnswer = (answer: string | null | undefined) => {
    if (!answer) return "Нет ответа";
    
    // Пытаемся распарсить строку, если она похожа на JSON
    if (answer.trim().startsWith('{') || answer.trim().startsWith('[')) {
        try {
            const parsed = JSON.parse(answer);
            
            // Если это объект (словарь пар: {"Ключ": "Значение"})
            if (typeof parsed === 'object' && !Array.isArray(parsed) && parsed !== null) {
                return (
                    <div className="flex flex-col gap-1.5 mt-1">
                        {Object.entries(parsed).map(([key, value], i) => (
                            <div key={i} className="flex items-start gap-2 bg-white/50 p-2 rounded-lg">
                                <span className="font-bold opacity-70">{key}</span>
                                <span className="opacity-50">➔</span>
                                <span className="font-extrabold">{String(value)}</span>
                            </div>
                        ))}
                    </div>
                );
            }
            
            // Если это массив (например: ["А", "Б"] или [["А","1"]])
            if (Array.isArray(parsed)) {
                return (
                    <div className="flex flex-col gap-1.5 mt-1">
                        {parsed.map((item, i) => (
                            <div key={i} className="bg-white/50 p-2 rounded-lg font-bold">
                                {Array.isArray(item) ? item.join(' ➔ ') : String(item)}
                            </div>
                        ))}
                    </div>
                );
            }
            
            return String(parsed);
        } catch (e) {
            // Если это не JSON, просто возвращаем строку
            return answer;
        }
    }
    
    return answer;
};
// ============================================================

export default function StudentTestReviewPage() {
    const { testId } = useParams();
    const [searchParams] = useSearchParams();
    const attemptId = searchParams.get('attempt_id');
    const navigate = useNavigate();

    const [feedback, setFeedback] = useState<AIFeedbackData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [currentIdx, setCurrentIdx] = useState(0);

    useEffect(() => {
        const fetchFeedback = async () => {
            const token = localStorage.getItem('access_token');
            if (!token || !attemptId) {
                console.error('Не передан ID попытки');
                setIsLoading(false);
                return;
            }

            try {
                const res = await fetch(`/api/v1/tests/${testId}/ai-feedback?attempt_id=${attemptId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!res.ok) throw new Error('Не удалось загрузить разбор');

                const data = await res.json();
                setFeedback(data);
            } catch (err: any) {
                console.error(err.message);
            } finally {
                setIsLoading(false);
            }
        };
        fetchFeedback();
    }, [testId, attemptId]);

    if (isLoading) {
        return <div className="min-h-screen flex items-center justify-center bg-[#f2f6f9] text-[#3b506c] font-bold">Загрузка разбора...</div>;
    }

    if (!feedback || !feedback.items || feedback.items.length === 0) {
        return (
            <div className="relative min-h-screen bg-[#f2f6f9] flex flex-col items-center justify-center p-6 text-center">
                <div className="fixed inset-0 bg-cover bg-center opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />
                <div className="relative z-10 bg-white/90 backdrop-blur-xl rounded-[40px] p-8 w-full max-w-[380px] shadow-2xl border border-white">
                    <div className="w-24 h-24 bg-[#e5f4e5] text-[#7FB280] mx-auto rounded-full flex items-center justify-center mb-6">
                        <Trophy size={48} />
                    </div>
                    <h2 className="text-[24px] font-extrabold text-[#3b506c] mb-2">Ошибок нет!</h2>
                    <p className="text-[14px] text-[#859bb1] font-bold mb-8">Ты ответил абсолютно на все вопросы правильно! Так держать!</p>
                    <Button onClick={() => navigate('/student')} className="w-full h-14 bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] font-extrabold text-[18px] rounded-full transition-all">
                        Вернуться на главную
                    </Button>
                </div>
            </div>
        );
    }

    const item = feedback.items[currentIdx];
    const totalQuestions = feedback.items.length;
    const progressPercent = ((currentIdx + 1) / totalQuestions) * 100;

    return (
        <div className="relative min-h-screen bg-[#f2f6f9] overflow-x-hidden flex justify-center font-sans pb-10">
            <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <div className="relative z-10 w-full max-w-[430px] flex flex-col">
                <header className="bg-white/80 backdrop-blur-md px-5 pt-6 pb-4 rounded-b-[30px] shadow-sm sticky top-0 z-20">
                    <div className="flex items-center justify-between mb-4">
                        <button
                            onClick={() => navigate('/student')}
                            className="w-10 h-10 bg-[#f2f6f9] rounded-xl flex items-center justify-center text-[#3b506c] hover:bg-[#e2eaf1] transition-colors"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        <div className="flex flex-col items-center">
                            <span className="text-[12px] font-bold text-[#D48B8B] uppercase tracking-wider">
                                Разбор ошибок
                            </span>
                            <span className="text-[16px] font-extrabold text-[#3b506c]">
                                Ошибка {currentIdx + 1} из {totalQuestions}
                            </span>
                        </div>
                        <div className="w-10 h-10" />
                    </div>

                    <div className="w-full h-2 bg-[#e2eaf1] rounded-full overflow-hidden">
                        <motion.div
                            className="h-full bg-[#D48B8B]"
                            initial={{ width: 0 }}
                            animate={{ width: `${progressPercent}%` }}
                            transition={{ duration: 0.3 }}
                        />
                    </div>
                </header>

                <div className="p-5 flex-1 flex flex-col">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={item.question_id}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ duration: 0.2 }}
                            className="flex-1"
                        >
                            {item.image_url && (
                                <div className="w-full mb-4 rounded-[20px] overflow-hidden border border-[#e2eaf1] bg-white shadow-sm">
                                    <img
                                        src={item.image_url}
                                        alt="Условие задачи"
                                        className="w-full max-h-[250px] object-contain"
                                    />
                                </div>
                            )}

                            <h2 className="text-[18px] font-extrabold text-[#3b506c] leading-snug mb-6 mt-2">
                                {item.question}
                            </h2>

                            <div className="flex flex-col gap-4">
                                {/* Твой (неверный) ответ */}
                                <div className="bg-[#f8e8e8]/60 border border-[#D48B8B]/30 rounded-[20px] p-4 relative overflow-hidden">
                                    <div className="flex items-center gap-2 mb-2 text-[#D48B8B]">
                                        <XCircle size={18} />
                                        <span className="text-[12px] font-extrabold uppercase tracking-wide">Твой ответ</span>
                                    </div>
                                    <div className="text-[15px] font-bold text-[#a85a5a] line-through decoration-[#D48B8B]/50">
                                        {formatAnswer(item.your_answer)}
                                    </div>
                                </div>

                                {/* Правильный ответ */}
                                <div className="bg-[#e5f4e5]/60 border border-[#7FB280]/30 rounded-[20px] p-4 relative overflow-hidden">
                                    <div className="flex items-center gap-2 mb-2 text-[#7FB280]">
                                        <CheckCircle2 size={18} />
                                        <span className="text-[12px] font-extrabold uppercase tracking-wide">Правильный ответ</span>
                                    </div>
                                    <div className="text-[15px] font-extrabold text-[#4a7a4c]">
                                        {formatAnswer(item.correct_answer)}
                                    </div>
                                </div>

                                {/* Объяснение от ИИ */}
                                {item.explanation && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: 0.2 }}
                                        className="bg-[#EBF1F1] border border-[#94A9BE]/30 rounded-[20px] p-4 mt-2 relative overflow-hidden"
                                    >
                                        <div className="absolute top-0 right-0 w-16 h-16 bg-[#94A9BE]/10 rounded-bl-full -z-10" />
                                        <div className="flex items-center gap-2 mb-2 text-[#596070]">
                                            <Lightbulb size={18} className="text-[#94A9BE]" />
                                            <span className="text-[12px] font-extrabold uppercase tracking-wide">Объяснение ИИ</span>
                                        </div>
                                        <p className="text-[14px] font-bold text-[#596070] leading-relaxed">
                                            {item.explanation}
                                        </p>
                                    </motion.div>
                                )}
                            </div>
                        </motion.div>
                    </AnimatePresence>
                </div>

                <div className="p-5 sticky bottom-0 bg-gradient-to-t from-[#f2f6f9] via-[#f2f6f9] to-transparent z-20 mt-auto">
                    <div className="flex gap-3">
                        {currentIdx > 0 && (
                            <Button
                                onClick={() => setCurrentIdx(prev => prev - 1)}
                                className="w-[30%] h-14 bg-white text-[#3b506c] font-extrabold text-[16px] rounded-full shadow-sm hover:bg-gray-50 transition-all"
                            >
                                Назад
                            </Button>
                        )}

                        {currentIdx < totalQuestions - 1 ? (
                            <Button
                                onClick={() => setCurrentIdx(prev => prev + 1)}
                                className="flex-1 h-14 bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] font-extrabold text-[16px] rounded-full shadow-md transition-all"
                            >
                                Следующая ошибка
                            </Button>
                        ) : (
                            <Button
                                onClick={() => navigate('/student')}
                                className="flex-1 h-14 bg-[#94A9BE] hover:bg-[#859bb1] text-white font-extrabold text-[16px] rounded-full shadow-md transition-all"
                            >
                                Завершить разбор
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
