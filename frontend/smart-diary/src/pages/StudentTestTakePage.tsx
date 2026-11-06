import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, CheckCircle2, XCircle, Award, AlertCircle } from 'lucide-react';
import { Button } from "../../@/components/ui/button";
import bgImage from '../assets/bg.png';
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/Errors';

interface TestQuestion {
    question_id: number;
    type: string;
    question: string;
    options?: any;
    image_url?: string | null;
}

interface TestData {
    test_id: number;
    topic_id: number;
    questions: TestQuestion[];
}

interface SubmitResult {
    attempt_id: number;
    score: number;
    passed: boolean;
}

export default function StudentTestTakePage() {
    const { testId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();

    const preloadedTest = location.state?.preloadedTest;
    const isPrepTest = location.state?.isPrep;

    const [test, setTest] = useState<TestData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    const [currentIdx, setCurrentIdx] = useState(0);
    const [answers, setAnswers] = useState<Record<number, string | string[]>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);
    const [result, setResult] = useState<SubmitResult | null>(null);

    useEffect(() => {
        if (preloadedTest) {
            setTest(preloadedTest);
            setIsLoading(false);
            return;
        }

        const fetchTest = async () => {
            try {
                const data = await apiFetch<TestData>(`/tests/${testId}`);
                setTest(data);
            } catch (err) {
                setErrorMsg(getErrorMessage(err));
            } finally {
                setIsLoading(false);
            }
        };
        fetchTest();
    }, [testId, preloadedTest]);

    // --- ПАРСЕР ОПЦИЙ (по Swagger options = object) ---
    const extractOptions = (opts: any): string[] => {
        if (!opts) return [];

        if (typeof opts === 'string') {
            try {
                return extractOptions(JSON.parse(opts));
            } catch { return []; }
        }

        if (Array.isArray(opts)) {
            return opts.map(o => typeof o === 'string' ? o : (o.text || o.label || JSON.stringify(o)));
        }

        if (typeof opts === 'object') {
            const values = Object.values(opts);
            if (values.length > 0 && values.every(v => typeof v === 'string')) {
                return values as string[];
            }
            for (const key of Object.keys(opts)) {
                if (Array.isArray(opts[key])) {
                    return extractOptions(opts[key]);
                }
            }
        }

        return [];
    };

    const handleSelectOption = (questionId: number, optionText: string, isMultiple: boolean) => {
        setAnswers(prev => {
            const currentAnswer = prev[questionId];

            if (isMultiple) {
                let arr = Array.isArray(currentAnswer) ? [...currentAnswer] : [];
                if (arr.includes(optionText)) {
                    arr = arr.filter(t => t !== optionText);
                } else {
                    arr.push(optionText);
                }
                return { ...prev, [questionId]: arr };
            } else {
                return { ...prev, [questionId]: optionText };
            }
        });
    };

    const handleTextInput = (questionId: number, value: string) => {
        setAnswers(prev => ({ ...prev, [questionId]: value }));
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        setSubmitError(null);

        const formattedAnswers = Object.entries(answers).map(([qId, ans]) => ({
            question_id: Number(qId),
            answer: Array.isArray(ans) ? ans.join(',') : String(ans)
        }));

        try {
            const submitData = await apiFetch<SubmitResult>(`/tests/${testId}/submit`, {
                method: 'POST',
                json: { answers: formattedAnswers }
            });
            setResult(submitData);
        } catch (err) {
            setSubmitError(getErrorMessage(err));
        } finally {
            setIsSubmitting(false);
        }
    };

    // --- РЕНДЕР ЭКРАНА РЕЗУЛЬТАТОВ ---
    if (result) {
        return (
            <div className="relative min-h-screen bg-[#f2f6f9] overflow-x-hidden flex flex-col items-center justify-center font-sans p-6">
                <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

                <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="relative z-10 bg-white/90 backdrop-blur-xl rounded-[40px] p-8 w-full max-w-[380px] text-center shadow-2xl border border-white"
                >
                    <div className={`w-24 h-24 mx-auto rounded-full flex items-center justify-center mb-6 ${result.passed ? 'bg-[#e5f4e5] text-[#7FB280]' : 'bg-[#f8e8e8] text-[#D48B8B]'}`}>
                        {result.passed ? <Award size={48} /> : <XCircle size={48} />}
                    </div>

                    <h1 className="text-[28px] font-extrabold text-[#3b506c] mb-2">
                        {result.passed ? 'Отлично!' : 'Почти получилось'}
                    </h1>
                    <p className="text-[16px] font-bold text-[#859bb1] mb-6">
                        Вы набрали <span className="text-[#3b506c] text-[20px]">{result.score}</span> баллов
                    </p>

                    <div className="bg-[#f7fafc] rounded-2xl p-4 mb-8">
                        <p className="text-[13px] font-bold text-[#556b86] leading-snug">
                            {result.passed
                                ? 'Ты отлично справился с заданием! Продолжай в том же духе'
                                : 'Не расстраивайся, посмотри разбор ошибок и попробуй еще раз'}
                        </p>
                    </div>

                    <div className="flex flex-col gap-3">
                        <Button
                            onClick={() => navigate(`/student/tests/${testId}/review?attempt_id=${result.attempt_id}`)}
                            className="w-full h-14 bg-[#94A9BE] hover:bg-[#859bb1] text-white font-extrabold text-[16px] rounded-full transition-all shadow-md"
                        >
                            Разбор ошибок
                        </Button>

                        <Button
                            onClick={() => navigate('/student')}
                            className="w-full h-14 bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] font-extrabold text-[16px] rounded-full transition-all"
                        >
                            Вернуться на главную
                        </Button>
                    </div>
                </motion.div>
            </div>
        );
    }

    if (isLoading) {
        return <div className="min-h-screen flex items-center justify-center bg-[#f2f6f9] text-[#3b506c] font-bold">Загрузка теста...</div>;
    }

    if (errorMsg || !test || !test.questions || test.questions.length === 0) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-[#f2f6f9] p-6 text-center">
                <XCircle size={60} className="text-[#D48B8B] mb-4" />
                <h2 className="text-xl font-bold text-[#3b506c] mb-4">{errorMsg || "В тесте нет вопросов"}</h2>
                <Button onClick={() => navigate(-1)} className="bg-[#B2CDE0] text-[#3b506c] rounded-full px-8">Назад</Button>
            </div>
        );
    }

    const question = test.questions[currentIdx];
    const totalQuestions = test.questions.length;
    const progressPercent = ((currentIdx + 1) / totalQuestions) * 100;

    const hasAnswered = answers[question.question_id] !== undefined &&
        (Array.isArray(answers[question.question_id])
            ? (answers[question.question_id] as string[]).length > 0
            : answers[question.question_id] !== '');

    const parsedOptions = extractOptions(question.options);

    const isChoiceType = question.type.includes('choice') || question.type === 'single_choice' || question.type === 'multiple_choice';
    const isMultiple = question.type === 'multiple_choice';
    const isTextInput = question.type === 'text_input' || question.type === 'math' || question.type === 'numeric';

    return (
        <div className="relative min-h-screen bg-[#f2f6f9] overflow-x-hidden flex justify-center font-sans pb-10">
            <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <div className="relative z-10 w-full max-w-[430px] flex flex-col">
                <header className="bg-white/80 backdrop-blur-md px-5 pt-6 pb-4 rounded-b-[30px] shadow-sm sticky top-0 z-20">
                    <div className="flex items-center justify-between mb-4">
                        <button
                            onClick={() => {
                                if (window.confirm("Вы уверены, что хотите выйти? Прогресс не сохранится.")) navigate(-1);
                            }}
                            className="w-10 h-10 bg-[#f2f6f9] rounded-xl flex items-center justify-center text-[#3b506c] hover:bg-[#e2eaf1] transition-colors"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        <div className="flex flex-col items-center">
                            <span className="text-[12px] font-bold text-[#94A9BE] uppercase tracking-wider">
                                {isPrepTest ? 'Тест для подготовки' : 'Тестирование'}
                            </span>
                            <span className="text-[16px] font-extrabold text-[#3b506c]">
                                Вопрос {currentIdx + 1} из {totalQuestions}
                            </span>
                        </div>
                        <div className="w-10 h-10" />
                    </div>

                    <div className="w-full h-2 bg-[#e2eaf1] rounded-full overflow-hidden">
                        <motion.div
                            className="h-full bg-[#94A9BE]"
                            initial={{ width: 0 }}
                            animate={{ width: `${progressPercent}%` }}
                            transition={{ duration: 0.3 }}
                        />
                    </div>
                </header>

                <div className="p-5 flex-1 flex flex-col">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={question.question_id}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ duration: 0.2 }}
                            className="flex-1"
                        >
                                                        {/* 👇 ОТОБРАЖЕНИЕ КАРТИНКИ УСЛОВИЯ 👇 */}
                            {question.image_url && (
                                <div className="w-full mb-4 rounded-[20px] overflow-hidden border border-[#e2eaf1] bg-white shadow-sm">
                                    <img 
                                        src={question.image_url} 
                                        alt="Условие задачи" 
                                        className="w-full max-h-[250px] object-contain" 
                                    />
                                </div>
                            )}

                            <h2 className="text-[20px] font-extrabold text-[#3b506c] leading-snug mb-6 mt-2">
                                {question.question}
                            </h2>

                            {/* РЕНДЕР ВАРИАНТОВ ВЫБОРА */}
                            {(isChoiceType || parsedOptions.length > 0) && (
                                parsedOptions.length > 0 ? (
                                    <div className="flex flex-col gap-3">
                                        {parsedOptions.map((opt, i) => {
                                            const isSelected = isMultiple
                                                ? ((answers[question.question_id] as string[]) || []).includes(opt)
                                                : answers[question.question_id] === opt;

                                            return (
                                                <motion.button
                                                    key={i}
                                                    whileTap={{ scale: 0.98 }}
                                                    onClick={() => handleSelectOption(question.question_id, opt, isMultiple)}
                                                    className={`w-full p-4 rounded-[20px] text-left font-bold text-[15px] transition-all border-2 flex items-center justify-between ${
                                                        isSelected
                                                            ? 'bg-[#B2CDE0]/20 border-[#94A9BE] text-[#3b506c]'
                                                            : 'bg-white/80 border-transparent text-[#556b86] hover:bg-white'
                                                    }`}
                                                >
                                                    <span className="pr-4">{opt}</span>
                                                    <div className={`w-6 h-6 shrink-0 flex items-center justify-center border-2 transition-colors ${
                                                        isMultiple ? 'rounded-md' : 'rounded-full'
                                                    } ${isSelected ? 'bg-[#94A9BE] border-[#94A9BE] text-white' : 'border-[#C9D9E6]'}`}>
                                                        {isSelected && <CheckCircle2 size={16} />}
                                                    </div>
                                                </motion.button>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <div className="bg-[#f8e8e8] border border-[#D48B8B]/30 p-5 rounded-[20px] text-center">
                                        <AlertCircle className="mx-auto text-[#D48B8B] mb-2" size={28} />
                                        <p className="font-bold text-[#D48B8B] text-sm">Не удалось загрузить варианты ответов</p>
                                        <p className="text-[12px] text-[#859bb1] mt-1">Скорее всего, бэкенд прислал пустой объект. Проверьте консоль (F12).</p>
                                    </div>
                                )
                            )}

                            {/* РЕНДЕР ТЕКСТОВОГО ОТВЕТА */}
                            {(!isChoiceType || isTextInput) && parsedOptions.length === 0 && (
                                <div className="mt-4">
                                    <input
                                        type={question.type === 'math' || question.type === 'numeric' ? 'number' : 'text'}
                                        value={(answers[question.question_id] as string) || ''}
                                        onChange={(e) => handleTextInput(question.question_id, e.target.value)}
                                        placeholder="Введите ваш ответ..."
                                        className="w-full bg-white/80 p-4 rounded-[20px] font-bold text-[18px] text-[#3b506c] outline-none focus:ring-4 focus:ring-[#B2CDE0]/50 transition-all border-2 border-transparent focus:border-[#94A9BE]"
                                        autoComplete="off"
                                    />
                                </div>
                            )}
                        </motion.div>
                    </AnimatePresence>
                </div>

                <div className="p-5 sticky bottom-0 bg-gradient-to-t from-[#f2f6f9] via-[#f2f6f9] to-transparent z-20 mt-auto">
                    
                    {/* 👇 БЛОК ВЫВОДА ОШИБКИ ОТПРАВКИ 👇 */}
                    {submitError && (
                        <div className="mb-4 p-3 bg-[#f8e8e8] border border-[#D48B8B]/30 text-[#D48B8B] text-[13px] font-bold rounded-xl text-center leading-snug">
                            {submitError}
                        </div>
                    )}

                    <div className="flex gap-3">
                        {currentIdx > 0 && (
                            <Button
                                onClick={() => { setCurrentIdx(prev => prev - 1); setSubmitError(null); }}
                                className="w-[30%] h-14 bg-white text-[#3b506c] font-extrabold text-[16px] rounded-full shadow-sm hover:bg-gray-50 transition-all"
                            >
                                Назад
                            </Button>
                        )}

                        {currentIdx < totalQuestions - 1 ? (
                            <Button
                                onClick={() => { setCurrentIdx(prev => prev + 1); setSubmitError(null); }}
                                disabled={!hasAnswered}
                                className="flex-1 h-14 bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] font-extrabold text-[16px] rounded-full shadow-md transition-all disabled:opacity-50 disabled:bg-gray-300"
                            >
                                Следующий вопрос
                            </Button>
                        ) : (
                            <Button
                                onClick={handleSubmit}
                                disabled={isSubmitting || !hasAnswered}
                                className="flex-1 h-14 bg-[#7FB280] hover:bg-[#6fa070] text-white font-extrabold text-[16px] rounded-full shadow-md transition-all disabled:opacity-50 disabled:bg-gray-300"
                            >
                                {isSubmitting ? 'Отправка...' : 'Завершить тест'}
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}