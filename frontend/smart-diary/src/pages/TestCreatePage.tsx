import { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { Button } from "../../@/components/ui/button.tsx";
import bgImage from '@/assets/bg.png';
import homeIcon from '@/assets/Home-Logo.svg';
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/Errors.ts';

const QUESTION_TYPES = [
    { id: 'single_choice', label: 'Одиночный выбор' },
    { id: 'multiple_choice', label: 'Множественный выбор' },
    { id: 'matching', label: 'Сопоставление' },
    { id: 'text_input', label: 'Текстовый ответ' },
    { id: 'math', label: 'Математика' }
];

const MATH_SYMBOLS = [
    '+', '-', '*', '/', '^', '√',
    'π', '∞', 'Σ', '∫', 'Δ', 'α',
    'β', '≤', '≥', '≠', 'x²', 'x³',
    'sin', 'cos', 'tan', 'ctg', '(', ')'
];

const CustomSelect = ({ value, options, onChange, placeholder }: { value: string, options: {id: string, label: string}[], onChange: (val: string) => void, placeholder?: string }) => {
    const [isOpen, setIsOpen] = useState(false);
    const selectRef = useRef<HTMLDivElement>(null);
    const selectedOption = options.find(o => o.id === value);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (selectRef.current && !selectRef.current.contains(event.target as Node)) setIsOpen(false);
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    return (
        <div className="relative w-full" ref={selectRef}>
            <button type="button" onClick={() => setIsOpen(!isOpen)} className="w-full bg-[#F4F8F8] p-3 rounded-xl font-bold text-[#596070] text-sm flex justify-between items-center outline-none hover:bg-[#e8f0f0] transition-colors border border-transparent focus:border-[#94A9BE]">
                <span className={selectedOption ? 'text-[#596070]' : 'text-[#859bb1]'}>
                    {selectedOption ? selectedOption.label : (placeholder || 'Выберите...')}
                </span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}><polyline points="6 9 12 15 18 9"></polyline></svg>
            </button>
            <AnimatePresence>
                {isOpen && (
                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="absolute z-50 w-full mt-1 bg-white rounded-xl shadow-xl border border-[#C9D9E6] overflow-hidden max-h-60 overflow-y-auto">
                        {options.length === 0 ? (
                            <div className="p-3 text-sm font-bold text-[#859bb1] text-center">Нет данных</div>
                        ) : (
                            options.map(opt => (
                                <div key={opt.id} onClick={() => { onChange(opt.id); setIsOpen(false); }} className={`p-3 text-sm font-bold cursor-pointer transition-colors ${value === opt.id ? 'bg-[#94A9BE] text-white' : 'text-[#596070] hover:bg-[#F4F8F8]'}`}>
                                    {opt.label}
                                </div>
                            ))
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

interface Option { id: string; text: string; isCorrect: boolean; rightText?: string; }
interface Question { id: string; type: string; question: string; options: Option[]; correctAnswerText?: string; image_url?: string | null; }
interface Topic { topic_id: number; topic_title: string; }
interface TeacherClass { class_id: number; class_name: string; }
interface UserProfile { subject?: { subject_id: number; }; }

// ============================================================
// УНИВЕРСАЛЬНЫЙ ПАРСЕР ОТВЕТА БЭКЕНДА
// ============================================================

// Извлекает массив строк-вариантов и массив правильных индексов из любой формы options.
// Покрывает: массивы, {options: []}, {values: []}, {items: []}, {variants: []},
// [{text: "..."}], [{label: "..."}], {correct_indices: []}, {correct_index: 0} и т.д.
function extractOptionsAndAnswers(options: any, fallbackCorrectIndex: any): {
    optionsArr: string[],
    correctIdx: number[]
} {
    let optionsArr: string[] = [];
    let correctIdx: number[] = [];

    // --- 1. Если options сам по себе массив ---
    if (Array.isArray(options)) {
        optionsArr = options.map((x: any) => {
            if (typeof x === 'string') return x;
            if (x && typeof x === 'object') return String(x.text ?? x.label ?? x.value ?? x.title ?? x.name ?? '');
            return String(x ?? '');
        });
    }

    // --- 2. Если options — объект-обёртка ---
    if (!optionsArr.length && options && typeof options === 'object' && !Array.isArray(options)) {
        const arrayKeys = [
            'options', 'values', 'items', 'variants', 'answers',
            'choices', 'list', 'entries', 'variants_list', 'answer_options',
            'option_list', 'possible_answers', 'all_options'
        ];
        for (const key of arrayKeys) {
            const candidate = options[key];
            if (Array.isArray(candidate)) {
                optionsArr = candidate.map((x: any) => {
                    if (typeof x === 'string') return x;
                    if (x && typeof x === 'object') return String(x.text ?? x.label ?? x.value ?? x.title ?? x.name ?? '');
                    return String(x ?? '');
                });
                break;
            }
        }
    }

    // --- 3. Правильные индексы — перебираем ВСЕ возможные поля ---
    const collectIndices = (obj: any) => {
        if (!obj || typeof obj !== 'object') return;
        const indexKeys = [
            'correct_indices', 'correct_indexes', 'correct_options', 'correct_answers',
            'correct_index', 'correct_option_index', 'correct_option', 'answer_index',
            'answer_indices', 'right_indices', 'right_index', 'right_answer'
        ];
        for (const key of indexKeys) {
            const v = obj[key];
            if (Array.isArray(v)) {
                correctIdx = v.map((x: any) => Number(x)).filter((n: number) => !isNaN(n));
                return;
            }
            if (typeof v === 'number') {
                correctIdx = [v];
                return;
            }
            if (typeof v === 'string' && !isNaN(Number(v))) {
                correctIdx = [Number(v)];
                return;
            }
        }
    };

    if (options && typeof options === 'object') collectIndices(options);

    // Fallback: если не нашли внутри options — берём из q.correct_option_index
    if (correctIdx.length === 0 && fallbackCorrectIndex !== null && fallbackCorrectIndex !== undefined) {
        if (Array.isArray(fallbackCorrectIndex)) {
            correctIdx = fallbackCorrectIndex.map(Number).filter((n: number) => !isNaN(n));
        } else if (typeof fallbackCorrectIndex === 'number') {
            correctIdx = [fallbackCorrectIndex];
        } else if (typeof fallbackCorrectIndex === 'string' && !isNaN(Number(fallbackCorrectIndex))) {
            correctIdx = [Number(fallbackCorrectIndex)];
        }
    }

    return { optionsArr, correctIdx };
}

// Нормализует произвольный type от LLM к нашим 5 типам
function normalizeQuestionType(rawType: any, q: any, idx: number): string {
    const t = String(rawType || '').toLowerCase().replace(/[\s_\-]/g, '');

    // ---- numeric / math ----
    if ([
        'numeric', 'number', 'math', 'calculation', 'calculate',
        'equation', 'formula', 'число', 'вычисление', 'математика', 'цифра'
    ].includes(t)) return 'math';

    // ---- matching ----
    if ([
        'matching', 'match', 'pairs', 'correspondence', 'matchingpairs', 'pair',
        'сопоставление', 'пары', 'соответствие', 'соединение'
    ].includes(t)) return 'matching';

    // ---- text_input ----
    if ([
        'text', 'textinput', 'textanswer', 'input', 'shortanswer', 'short',
        'open', 'openanswer', 'essay', 'fillinblank', 'fill', 'blank', 'freeform',
        'freeanswer', 'текст', 'текстовый', 'ввод', 'открытый', 'свободный'
    ].includes(t)) return 'text_input';

    // ---- multiple_choice ----
    if ([
        'multiple', 'multiplechoice', 'multichoice', 'checkbox', 'checkboxes',
        'multi', 'manychoice', 'many', 'mcq', 'mc', 'multipleselection',
        'множественный', 'множественныйвыбор', 'чекбокс', 'несколько'
    ].includes(t)) return 'multiple_choice';

    // ---- single_choice ----
    if ([
        'single', 'singlechoice', 'onechoice', 'choice', 'radio', 'one',
        'options', 'option', 'scq', 'sc', 'singleselection', 'единственный',
        'одиночный', 'одиночныйвыбор', 'выбор', 'радио', 'один'
    ].includes(t)) return 'single_choice';

    // ---- Fallback: угадываем по структуре данных ----
    let guessed = 'text_input';
    if (q.numeric_answer !== null && q.numeric_answer !== undefined) {
        guessed = 'math';
    } else if (q.options && typeof q.options === 'object' &&
               (Array.isArray(q.options.left) || q.options.correct_matches)) {
        guessed = 'matching';
    } else if (q.options && typeof q.options === 'object' && (q.options.is_text || q.options.correct_text)) {
        guessed = 'text_input';
    } else {
        const { optionsArr } = extractOptionsAndAnswers(q.options, q.correct_option_index);
        if (optionsArr.length > 0) guessed = 'single_choice';
    }

    console.warn(`⚠️ Вопрос #${idx + 1}: неизвестный тип "${rawType}", угадали как "${guessed}"`, q);
    return guessed;
}

// Основной парсер одного вопроса
function parseBackendQuestion(q: any, idx: number = 0): {
    frontType: string,
    mappedOptions: Option[],
    correctAnswerText: string
} {
    const frontType = normalizeQuestionType(q.type, q, idx);

    let mappedOptions: Option[] = [];
    let correctAnswerText = '';

    if (frontType === 'matching') {
        const container = (q.options && typeof q.options === 'object' && !Array.isArray(q.options))
            ? q.options
            : {};
        const left: string[] = Array.isArray(container.left) ? container.left : [];
        const matches: Record<string, string> = (container.correct_matches && typeof container.correct_matches === 'object')
            ? container.correct_matches
            : {};
        mappedOptions = left.map((l: string, i: number) => ({
            id: String(i),
            text: l,
            isCorrect: false,
            rightText: matches[l] || ''
        }));
    } else if (frontType === 'math') {
        correctAnswerText = (q.numeric_answer !== null && q.numeric_answer !== undefined)
            ? String(q.numeric_answer)
            : '';
    } else if (frontType === 'text_input') {
        if (q.options && typeof q.options === 'object' && !Array.isArray(q.options)) {
            correctAnswerText = q.options.correct_text
                ?? q.options.text
                ?? q.options.answer
                ?? q.options.value
                ?? '';
        } else if (typeof q.options === 'string') {
            correctAnswerText = q.options;
        }
    } else {
        // single_choice / multiple_choice — основной кейс, который не работал
        const { optionsArr, correctIdx } = extractOptionsAndAnswers(q.options, q.correct_option_index);

        mappedOptions = optionsArr.map((text, i) => ({
            id: String(i),
            text,
            isCorrect: correctIdx.includes(i)
        }));
    }

    // Диагностика — оставим в проде, не помешает
    if (mappedOptions.length === 0 && frontType !== 'math' && frontType !== 'text_input') {
        console.warn(
            `⚠️ Вопрос #${idx + 1}: тип "${frontType}", но вариантов не найдено. ` +
            `Что реально пришло:`, JSON.parse(JSON.stringify(q))
        );
    }

    return { frontType, mappedOptions, correctAnswerText };
}

// ============================================================

export default function TestCreatePage() {
    const navigate = useNavigate();
    const { testId: urlTestId } = useParams();
    const isEditing = Boolean(urlTestId);

    const [testName, setTestName] = useState('Новый тест');
    const [testId, setTestId] = useState<number | null>(urlTestId ? Number(urlTestId) : null);

    const [classes, setClasses] = useState<TeacherClass[]>([]);
    const [selectedClass, setSelectedClass] = useState<string>('');
    const [topics, setTopics] = useState<Topic[]>([]);
    const [selectedTopic, setSelectedTopic] = useState<string>('');

    const [aiQuestionCount, setAiQuestionCount] = useState(5);
    const [questions, setQuestions] = useState<Question[]>([]);

    const [isGenerating, setIsGenerating] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isLoadingTest, setIsLoadingTest] = useState(false);
    const [generatingQuestionId, setGeneratingQuestionId] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState<string | null>(null);
    const [user, setUser] = useState<UserProfile | null>(null);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

    const showToast = (message: string, type: 'success' | 'error') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const [userData, topicsData, classesData] = await Promise.all([
                    apiFetch<UserProfile>('/users/me'),
                    apiFetch<Topic[]>('/teacher/topics'),
                    apiFetch<TeacherClass[]>('/teacher/classes')
                ]);

                setUser(userData);
                setTopics(topicsData);
                if (!isEditing && topicsData.length > 0) setSelectedTopic(topicsData[0].topic_id.toString());

                setClasses(classesData);
                if (!isEditing && classesData.length > 0) setSelectedClass(classesData[0].class_id.toString());

                if (isEditing && urlTestId) {
                    setIsLoadingTest(true);
                    const data = await apiFetch<any>(`/teacher/tests/${urlTestId}`);
                    setTestId(data.test_id);
                    setSelectedTopic(String(data.topic_id));
                    setTestName(`Тест #${data.test_id}`);

                    const mapped: Question[] = (data.questions || []).map((q: any, i: number) => {
                        const parsed = parseBackendQuestion(q, i);
                        return {
                            id: Math.random().toString(36).slice(2, 11),
                            type: parsed.frontType,
                            question: q.question || '',
                            options: parsed.mappedOptions,
                            correctAnswerText: parsed.correctAnswerText,
                            image_url: q.image_url || null
                        };
                    });
                    setQuestions(mapped);
                }
            } catch (err) {
                showToast(getErrorMessage(err), 'error');
            } finally {
                setIsLoadingTest(false);
            }
        };
        fetchInitialData();
    }, [urlTestId, isEditing]);

    const handleImageUpload = async (qId: string, file: File) => {
        setIsUploading(qId);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const token = localStorage.getItem('access_token');
            const res = await fetch('/api/v1/teacher/upload-image', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                updateQuestion(qId, 'image_url', data.image_url);
                showToast('Картинка загружена!', 'success');
            } else {
                showToast('Ошибка загрузки картинки', 'error');
            }
        } catch (err) {
            showToast('Ошибка сети', 'error');
        } finally {
            setIsUploading(null);
        }
    };

    const callAIGenerate = async (count: number, type: string | null = null) => {
        if (!selectedTopic || !selectedClass) {
            showToast('Выберите тему и класс', 'error');
            return null;
        }
        if (testId && !isEditing) {
            try {
                await apiFetch(`/teacher/tests/${testId}`, { method: 'DELETE' });
                setTestId(null);
<<<<<<< HEAD
            } catch (err) {
                // игнорируем ошибку удаления старого черновика
            }
=======
            } catch (err) {}
>>>>>>> 731874fcc9f32373ad7d7c8be720a08035fb9b09
        }

        try {
            const data = await apiFetch<any>('/teacher/tests/generate', {
                method: 'POST',
                json: {
                    topic_id: Number(selectedTopic),
                    subject_id: user?.subject?.subject_id || 3,
                    class_id: Number(selectedClass),
                    title: testName,
                    question_count: count,
                    question_type: type
                }
            });

<<<<<<< HEAD
            return {
                test_id: data.test_id,
                questions: (data.questions || []).map((q: any) => {
                    let frontType = q.type === 'numeric' ? 'math' : 'single_choice';
                    let optionTexts: string[] = [];
                    if (q.options && Array.isArray(q.options.options)) optionTexts = q.options.options;

                    const correctIdx = q.correct_option_index !== null && q.correct_option_index !== undefined ? [q.correct_option_index] : [];

                    return {
                        id: Math.random().toString(36).slice(2, 11),
                        type: frontType,
                        question: q.question || '',
                        options: optionTexts.map((text, i) => ({ id: String(i), text, isCorrect: correctIdx.includes(i) })),
                        correctAnswerText: q.numeric_answer !== null && q.numeric_answer !== undefined ? String(q.numeric_answer) : ''
=======
            console.log('📥 СЫРОЙ ОТВЕТ ОТ БЭКА /generate:', JSON.parse(JSON.stringify(data)));

            const rawQuestions: any[] = Array.isArray(data.questions)
                ? data.questions
                : (Array.isArray(data.questions?.value) ? data.questions.value : []);

            return {
                test_id: data.test_id,
                questions: rawQuestions.map((q: any, i: number) => {
                    const parsed = parseBackendQuestion(q, i);
                    return {
                        id: Math.random().toString(36).slice(2, 11),
                        type: parsed.frontType,
                        question: q.question || '',
                        options: parsed.mappedOptions,
                        correctAnswerText: parsed.correctAnswerText,
                        image_url: q.image_url || null
>>>>>>> 731874fcc9f32373ad7d7c8be720a08035fb9b09
                    };
                })
            };
        } catch (err) {
            showToast(getErrorMessage(err), 'error');
            return null;
        }
    };

    const handleGenerateAI = async () => {
        if (!selectedTopic || !selectedClass) return showToast('Выберите класс и тему', 'error');
        setIsGenerating(true);
        try {
            const result = await callAIGenerate(aiQuestionCount);
            if (result) {
                setQuestions(result.questions);
                setTestId(result.test_id);
                showToast(`Сгенерировано ${result.questions.length} вопросов!`, 'success');
            }
        } finally {
            setIsGenerating(false);
        }
    };

    const handleGenerateSingleAI = async (qId: string) => {
        if (!selectedTopic || !selectedClass) return showToast('Сначала выберите класс и тему', 'error');
        setGeneratingQuestionId(qId);
        const currentQ = questions.find(q => q.id === qId);
        try {
            const result = await callAIGenerate(1, currentQ?.type || 'single_choice');
            if (result && result.questions.length > 0) {
                const aiQuestion = result.questions[0];
                setQuestions(prev => prev.map(q => q.id === qId ? { ...aiQuestion, id: qId } : q));
                if (!testId && result.test_id) setTestId(result.test_id);
                showToast('Вопрос сгенерирован ИИ!', 'success');
            }
        } finally {
            setGeneratingQuestionId(null);
        }
    };

    const handleAddQuestion = () => {
        setQuestions(prev => [...prev, {
            id: Math.random().toString(36).slice(2, 11), type: 'single_choice', question: '',
            options: [{ id: '1', text: '', isCorrect: false }, { id: '2', text: '', isCorrect: false }], correctAnswerText: '', image_url: null
        }]);
    };

    const updateQuestion = (id: string, field: keyof Question, value: any) => {
        setQuestions(prev => prev.map(q => q.id === id ? { ...q, [field]: value } : q));
    };

    const handleTypeChange = (id: string, newType: string) => {
        setQuestions(prev => prev.map(q => {
            if (q.id !== id) return q;
            let newOptions = q.options;
            if (newType === 'text_input' || newType === 'math') newOptions = [];
            else if (newType === 'matching') newOptions = [{ id: '1', text: '', isCorrect: false, rightText: '' }];
            else if ((newType === 'single_choice' || newType === 'multiple_choice') && q.options.length === 0) {
                newOptions = [{ id: '1', text: '', isCorrect: false }, { id: '2', text: '', isCorrect: false }];
            }
            return { ...q, type: newType, options: newOptions, correctAnswerText: '' };
        }));
    };

    const updateOption = (qId: string, oId: string, text: string) => {
        setQuestions(prev => prev.map(q => q.id === qId ? { ...q, options: q.options.map(o => o.id === oId ? { ...o, text } : o) } : q));
    };

    const updateOptionRight = (qId: string, oId: string, rightText: string) => {
        setQuestions(prev => prev.map(q => q.id === qId ? { ...q, options: q.options.map(o => o.id === oId ? { ...o, rightText } : o) } : q));
    };

    const removeOption = (qId: string, oId: string) => {
        setQuestions(prev => prev.map(q => q.id === qId ? { ...q, options: q.options.filter(o => o.id !== oId) } : q));
    };

    const toggleCorrectOption = (qId: string, oId: string, isMultiple: boolean) => {
        setQuestions(prev => prev.map(q => {
            if (q.id !== qId) return q;
            return {
                ...q,
                options: q.options.map(o => {
                    if (o.id === oId) return { ...o, isCorrect: !o.isCorrect };
                    if (!isMultiple && o.id !== oId) return { ...o, isCorrect: false };
                    return o;
                })
            };
        }));
    };

    const handleSave = async () => {
        if (questions.length === 0) return showToast('Добавьте хотя бы один вопрос', 'error');
        if (!selectedTopic || !selectedClass) return showToast('Выберите класс и тему', 'error');

        setIsSaving(true);
        try {
            let currentTestId = testId;

            if (!currentTestId) {
                const genData = await apiFetch<{ test_id: number }>('/teacher/tests/generate', {
                    method: 'POST',
                    json: {
                        topic_id: Number(selectedTopic),
                        subject_id: user?.subject?.subject_id || 3,
                        class_id: Number(selectedClass),
                        question_count: 0,
                        question_type: null
                    }
                });
                currentTestId = genData.test_id;
                setTestId(currentTestId);
            }

            const payload = {
                topic_id: Number(selectedTopic),
                title: testName,
                questions: questions.map(q => {
                    const isChoice = q.type === 'single_choice' || q.type === 'multiple_choice';

                    if (q.type === 'matching') {
                        const left: string[] = [];
                        const right: string[] = [];
                        const correct_matches: Record<string, string> = {};

                        q.options.forEach(opt => {
                            if (opt.text.trim() && opt.rightText?.trim()) {
                                left.push(opt.text.trim());
                                right.push(opt.rightText.trim());
                                correct_matches[opt.text.trim()] = opt.rightText.trim();
                            }
                        });

                        return {
                            type: q.type,
                            question: q.question,
                            image_url: q.image_url || null,
                            options: { left, right, correct_matches },
                            correct_indices: null,
                            numeric_answer: null
                        };
                    }

                    return {
                        type: q.type,
                        question: q.question,
                        image_url: q.image_url || null,
                        options: isChoice
                            ? q.options.map(o => o.text)
                            : (q.type === 'text_input' ? [q.correctAnswerText || ''] : null),
                        correct_indices: isChoice
                            ? q.options.map((o, i) => o.isCorrect ? i : -1).filter(i => i !== -1)
                            : null,
                        numeric_answer: q.type === 'math' && q.correctAnswerText ? Number(q.correctAnswerText) : null
                    };
                })
            };

            await apiFetch(`/teacher/tests/${currentTestId}`, {
                method: 'PUT',
                json: payload
            });

            showToast(isEditing ? 'Изменения сохранены!' : 'Тест сохранён!', 'success');
            setTimeout(() => navigate('/teacher/tests'), 1500);
        } catch (err) {
            showToast(getErrorMessage(err), 'error');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="relative min-h-screen bg-[#F4F8F8] overflow-x-hidden flex justify-center pb-20 font-sans">
            <div className="fixed inset-0 bg-cover bg-center opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />
            <AnimatePresence>
                {toast && (
                    <motion.div initial={{ opacity: 0, y: -50, scale: 0.9 }} animate={{ opacity: 1, y: 20, scale: 1 }} exit={{ opacity: 0, y: -50, scale: 0.9 }} className={`fixed top-0 left-1/2 -translate-x-1/2 z-[100] pl-2 pr-6 py-2 rounded-full shadow-lg flex items-center gap-3 backdrop-blur-md border ${toast.type === 'success' ? 'bg-[#F4F8F8]/95 border-[#B2CDE0]' : 'bg-[#F4F8F8]/95 border-[#D48B8B]'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white ${toast.type === 'success' ? 'bg-[#94A9BE]' : 'bg-[#D48B8B]'}`}>
                            {toast.type === 'success' ? '✓' : '!'}
                        </div>
                        <span className="font-bold text-[14px] text-[#596070]">{toast.message}</span>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="relative z-10 w-full max-w-[440px] flex flex-col">
                <header className="bg-[#B2CDE0] px-6 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between sticky top-0 z-30">
                    <button onClick={() => navigate('/teacher/tests')} className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors">
                        <img src={homeIcon} alt="Home" className="w-full h-full object-contain" />
                    </button>
                    <h1 className="text-[24px] font-extrabold text-[#596070] tracking-wide">
                        {isEditing ? 'Редактирование' : 'Конструктор'}
                    </h1>
                    <div className="w-12 h-12" />
                </header>

                <div className="mt-6 px-4 flex flex-col gap-6">
                    {!isEditing && (
                        <div className="bg-white/80 backdrop-blur-md rounded-[30px] p-5 shadow-sm border border-white/50 flex flex-col gap-4">
                            <div>
                                <label className="block text-[#596070] font-bold text-sm mb-1">Название теста</label>
                                <input
                                    value={testName}
                                    onChange={e => setTestName(e.target.value)}
                                    className="w-full bg-[#F4F8F8] p-3 rounded-xl font-bold text-[#596070] outline-none focus:ring-2 focus:ring-[#94A9BE] transition-all"
                                    placeholder="Введите название..."
                                />
                            </div>

                            <div>
                                <label className="block text-[#596070] font-bold text-sm mb-1">Класс</label>
                                <CustomSelect
                                    value={selectedClass}
                                    options={classes.map(c => ({ id: c.class_id.toString(), label: c.class_name }))}
                                    onChange={setSelectedClass}
                                    placeholder="Выберите класс..."
                                />
                            </div>

                            <div>
                                <label className="block text-[#596070] font-bold text-sm mb-1">Тема (для генерации)</label>
                                <CustomSelect
                                    value={selectedTopic}
                                    options={topics.map(t => ({ id: t.topic_id.toString(), label: t.topic_title }))}
                                    onChange={setSelectedTopic}
                                    placeholder="Выберите тему..."
                                />
                            </div>

                            <div className="flex items-center justify-between bg-[#F4F8F8] p-3 rounded-xl mt-2">
                                <span className="font-bold text-[#596070] text-sm">Вопросов от ИИ</span>
                                <div className="flex items-center gap-3">
                                    <button onClick={() => setAiQuestionCount(Math.max(1, aiQuestionCount - 1))} className="w-8 h-8 bg-white rounded-full font-bold text-lg text-[#596070] shadow-sm flex items-center justify-center">-</button>
                                    <span className="text-lg font-extrabold text-[#596070] w-4 text-center">{aiQuestionCount}</span>
                                    <button onClick={() => setAiQuestionCount(Math.min(20, aiQuestionCount + 1))} className="w-8 h-8 bg-white rounded-full font-bold text-lg text-[#596070] shadow-sm flex items-center justify-center">+</button>
                                </div>
                            </div>

                            <Button
                                onClick={handleGenerateAI}
                                disabled={isGenerating || classes.length === 0 || topics.length === 0}
                                className="w-full h-[50px] bg-[#94A9BE] hover:bg-[#859bb1] text-white rounded-xl text-[16px] font-extrabold shadow-md transition-all mt-1 disabled:opacity-50"
                            >
                                {isGenerating ? 'Генерация ИИ...' : 'Сгенерировать весь тест (ИИ)'}
                            </Button>

                            {testId && (
                                <p className="text-center text-[12px] font-bold text-[#859bb1]">
                                    Черновик создан (ID: {testId})
                                </p>
                            )}
                        </div>
                    )}

                    {isEditing && (
                        <div className="bg-white/80 backdrop-blur-md rounded-[30px] p-5 shadow-sm border border-white/50">
                            <p className="text-center font-bold text-[#596070] text-sm">
                                {isLoadingTest ? 'Загрузка теста...' : 'Редактирование теста по теме:'}
                            </p>
                            {!isLoadingTest && (
                                <p className="text-center text-[#94A9BE] font-extrabold text-base mt-1">
                                    {topics.find(t => t.topic_id.toString() === selectedTopic)?.topic_title || `Тема #${selectedTopic}`}
                                </p>
                            )}
                            {testId && (
                                <p className="text-center text-[12px] font-bold text-[#859bb1] mt-2">ID: {testId}</p>
                            )}
                        </div>
                    )}

                    {isLoadingTest && (
                        <div className="flex justify-center mt-10">
                            <div className="w-8 h-8 border-4 border-[#94A9BE] border-t-transparent rounded-full animate-spin" />
                        </div>
                    )}

                    {!isLoadingTest && (
                        <div className="flex flex-col gap-4">
                            {questions.map((q, qIndex) => (
                                <motion.div
                                    key={q.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="bg-white/80 backdrop-blur-md rounded-[30px] p-5 shadow-sm border border-white/50 relative overflow-hidden"
                                >
                                    {generatingQuestionId === q.id && (
                                        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center">
                                            <div className="w-6 h-6 border-4 border-[#94A9BE] border-t-transparent rounded-full animate-spin mb-2" />
                                            <span className="text-[#596070] font-bold text-sm">ИИ думает...</span>
                                        </div>
                                    )}

                                    <div className="flex justify-between items-center mb-3">
                                        <span className="font-extrabold text-[#596070] text-lg">Вопрос {qIndex + 1}</span>
                                        <div className="flex gap-2">
                                            {!isEditing && (
                                                <button
                                                    onClick={() => handleGenerateSingleAI(q.id)}
                                                    className="text-[#94A9BE] bg-[#F4F8F8] px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1 hover:bg-[#e8f0f0] transition-colors"
                                                >
                                                    ✨ ИИ
                                                </button>
                                            )}
                                            <button
                                                onClick={() => setQuestions(prev => prev.filter(x => x.id !== q.id))}
                                                className="text-[#D48B8B] bg-[#F4F8F8] px-3 py-1.5 rounded-lg font-bold text-xs hover:bg-[#f8e8e8] transition-colors"
                                            >
                                                Удалить
                                            </button>
                                        </div>
                                    </div>

                                    <div className="flex flex-col gap-3 relative z-0">
                                        <CustomSelect
                                            value={q.type}
                                            options={QUESTION_TYPES}
                                            onChange={(val) => handleTypeChange(q.id, val)}
                                        />

                                        <div className="flex flex-col gap-2">
                                            <textarea
                                                value={q.question}
                                                onChange={(e) => updateQuestion(q.id, 'question', e.target.value)}
                                                placeholder="Текст вопроса..."
                                                className="w-full bg-[#F4F8F8] p-3 rounded-xl font-bold text-[#596070] outline-none resize-none h-20 text-sm focus:ring-2 focus:ring-[#94A9BE] transition-all"
                                            />

                                            {q.type === 'math' && (
                                                <div className="grid grid-cols-6 gap-1.5">
                                                    {MATH_SYMBOLS.map(symbol => (
                                                        <button
                                                            key={symbol}
                                                            onMouseDown={(e) => e.preventDefault()}
                                                            onClick={() => {
                                                                const currentVal = q.question || '';
                                                                updateQuestion(q.id, 'question', currentVal + symbol);
                                                            }}
                                                            className="h-9 bg-[#EBF1F1] rounded-lg text-[#3b506c] font-extrabold text-[14px] hover:bg-[#B2CDE0] transition-colors shadow-sm flex items-center justify-center"
                                                        >
                                                            {symbol}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>

                                        <div className="flex flex-col gap-2 mt-1">
                                            {q.image_url ? (
                                                <div className="relative w-full h-32 rounded-xl overflow-hidden border border-[#C9D9E6] group">
                                                    <img src={q.image_url} alt="Условие" className="w-full h-full object-contain bg-black/5" />
                                                    <button
                                                        onClick={() => updateQuestion(q.id, 'image_url', null)}
                                                        className="absolute top-2 right-2 bg-red-500 text-white p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity"
                                                    >
                                                        ✕
                                                    </button>
                                                </div>
                                            ) : (
                                                <label className={`flex items-center justify-center w-full h-12 bg-[#F4F8F8] border-2 border-dashed border-[#C9D9E6] rounded-xl cursor-pointer hover:bg-[#e8f0f0] transition-colors ${isUploading === q.id ? 'opacity-50 pointer-events-none' : ''}`}>
                                                    <span className="text-[#859bb1] font-bold text-sm flex items-center gap-2">
                                                        {isUploading === q.id ? 'Загрузка...' : '📷 Прикрепить картинку'}
                                                    </span>
                                                    <input
                                                        type="file"
                                                        accept="image/jpeg,image/png,image/webp"
                                                        className="hidden"
                                                        onChange={(e) => {
                                                            const file = e.target.files?.[0];
                                                            if (file) handleImageUpload(q.id, file);
                                                        }}
                                                    />
                                                </label>
                                            )}
                                        </div>

                                        {(q.type === 'single_choice' || q.type === 'multiple_choice') && (
                                            <div className="flex flex-col gap-2 mt-1">
                                                {q.options.length === 0 && (
                                                    <p className="text-[12px] text-[#D48B8B] font-bold">
                                                        ⚠️ Варианты не найдены. Добавь вручную или нажми «✨ ИИ»
                                                    </p>
                                                )}
                                                {q.options.map((opt, oIndex) => (
                                                    <div key={opt.id} className="flex items-center gap-2">
                                                        <button
                                                            onClick={() => toggleCorrectOption(q.id, opt.id, q.type === 'multiple_choice')}
                                                            className={`w-6 h-6 shrink-0 rounded-md flex items-center justify-center border-2 transition-colors ${
                                                                opt.isCorrect ? 'bg-[#94A9BE] border-[#94A9BE] text-white' : 'border-[#C9D9E6]'
                                                            }`}
                                                        >
                                                            {opt.isCorrect && '✓'}
                                                        </button>
                                                        <input
                                                            value={opt.text}
                                                            onChange={(e) => updateOption(q.id, opt.id, e.target.value)}
                                                            placeholder={`Вариант ${oIndex + 1}`}
                                                            className="flex-1 bg-[#F4F8F8] p-2 rounded-lg font-bold text-[#596070] text-sm outline-none focus:ring-2 focus:ring-[#94A9BE] transition-all"
                                                        />
                                                    </div>
                                                ))}
                                                <button
                                                    onClick={() => updateQuestion(q.id, 'options', [...q.options, { id: Date.now().toString(), text: '', isCorrect: false }])}
                                                    className="text-[#94A9BE] font-bold text-xs text-left mt-1 hover:underline"
                                                >
                                                    + Добавить вариант
                                                </button>
                                            </div>
                                        )}

                                        {q.type === 'matching' && (
                                            <div className="flex flex-col gap-2 mt-2">
                                                <label className="block text-[#596070] font-bold text-xs mb-1">Пары (Левое и Правое)</label>
                                                {q.options.length === 0 && (
                                                    <p className="text-[12px] text-[#D48B8B] font-bold">
                                                        ⚠️ Пары не найдены. Добавь вручную.
                                                    </p>
                                                )}
                                                {q.options.map((opt) => (
                                                    <div key={opt.id} className="flex items-center gap-2">
                                                        <input
                                                            value={opt.text}
                                                            onChange={(e) => updateOption(q.id, opt.id, e.target.value)}
                                                            placeholder="Левая часть"
                                                            className="flex-1 bg-[#F4F8F8] p-2 rounded-lg font-bold text-[#596070] text-sm outline-none focus:ring-2 focus:ring-[#94A9BE] transition-all"
                                                        />
                                                        <span className="text-[#859bb1]">-</span>
                                                        <input
                                                            value={opt.rightText || ''}
                                                            onChange={(e) => updateOptionRight(q.id, opt.id, e.target.value)}
                                                            placeholder="Правая часть"
                                                            className="flex-1 bg-[#F4F8F8] p-2 rounded-lg font-bold text-[#596070] text-sm outline-none focus:ring-2 focus:ring-[#94A9BE] transition-all"
                                                        />
                                                        <button onClick={() => removeOption(q.id, opt.id)} className="text-[#D48B8B] p-1">
                                                            <X size={16}/>
                                                        </button>
                                                    </div>
                                                ))}
                                                <button
                                                    onClick={() => updateQuestion(q.id, 'options', [...q.options, { id: Date.now().toString(), text: '', isCorrect: false, rightText: '' }])}
                                                    className="text-[#94A9BE] font-bold text-xs text-left mt-1 hover:underline"
                                                >
                                                    + Добавить пару
                                                </button>
                                            </div>
                                        )}

                                        {(q.type === 'math' || q.type === 'text_input') && (
                                            <div className="mt-2 flex flex-col gap-2">
                                                <input
                                                    value={q.correctAnswerText || ''}
                                                    onChange={(e) => updateQuestion(q.id, 'correctAnswerText', e.target.value)}
                                                    placeholder={q.type === 'math' ? 'Правильный ответ (число)' : 'Правильный текстовый ответ'}
                                                    className="w-full bg-[#F4F8F8] p-3 rounded-xl font-bold text-[#596070] text-sm outline-none focus:ring-2 focus:ring-[#94A9BE] transition-all border border-dashed border-[#C9D9E6]"
                                                />

                                                {q.type === 'math' && (
                                                    <div className="grid grid-cols-6 gap-1.5 mt-1">
                                                        {MATH_SYMBOLS.map(symbol => (
                                                            <button
                                                                key={symbol}
                                                                onMouseDown={(e) => e.preventDefault()}
                                                                onClick={() => {
                                                                    const currentVal = q.correctAnswerText || '';
                                                                    updateQuestion(q.id, 'correctAnswerText', currentVal + symbol);
                                                                }}
                                                                className="h-9 bg-[#EBF1F1] rounded-lg text-[#3b506c] font-extrabold text-[14px] hover:bg-[#B2CDE0] transition-colors shadow-sm flex items-center justify-center"
                                                            >
                                                                {symbol}
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}

                    <div className="flex flex-col gap-3 mt-4 mb-10">
                        <Button
                            onClick={handleAddQuestion}
                            className="w-full h-[60px] bg-white/60 hover:bg-white/80 border-2 border-[#94A9BE] text-[#596070] rounded-full text-[18px] font-extrabold transition-all"
                        >
                            + Добавить вопрос вручную
                        </Button>

                        <Button
                            onClick={handleSave}
                            disabled={isSaving || questions.length === 0 || isLoadingTest}
                            className="w-full h-[60px] bg-[#94A9BE] hover:bg-[#859bb1] text-white rounded-full text-[18px] font-extrabold shadow-md transition-all disabled:opacity-50"
                        >
                            {isSaving ? 'Сохранение...' : (isEditing ? 'Сохранить изменения' : 'Сохранить тест')}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
