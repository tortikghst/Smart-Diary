import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from "../../@/components/ui/button.tsx";
import bgImage from '@/assets/bg.png';
import homeIcon from '@/assets/Home-Logo.svg';
import journalIcon from '@/assets/Journal-Logo.svg';
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/Errors.ts';

interface TopicAvg {
    topic_id: number;
    topic_title: string;
    avg_score: number;
    mastery_percent: number;
    students_with_gaps: number;
}

interface AnalyticsData {
    class_id: number;
    big_numbers: { avg_score: number | null; active_debts: number; };
    grade_distribution: { grade_5: number; grade_4: number; grade_3: number; grade_2: number; };
    topics_avg: TopicAvg[];
    weakest_topic: TopicAvg | null;
    ai_recommendation: string | null;
}

type MetricType = 'avg' | 'debts' | 'weak' | null;

export default function ClassPage() {
    const { classId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const scrollRef = useRef<HTMLDivElement>(null);
    const labelsScrollRef = useRef<HTMLDivElement>(null);

    const displayClassName = location.state?.className ? `${location.state.className} КЛАСС` : `${classId} КЛАСС`;

    const [data, setData] = useState<AnalyticsData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeChart, setActiveChart] = useState<'bar' | 'pie'>('bar');
    const [topicIndex, setTopicIndex] = useState(0);

    const [aiRecommendation, setAiRecommendation] = useState<string | null>(null);
    const [isAiLoading, setIsAiLoading] = useState(true);

    const [activeMetric, setActiveMetric] = useState<MetricType>(null);

    useEffect(() => {
        const fetchAnalytics = async () => {
            setIsLoading(true);
            setError(null);
            try {
                const res = await apiFetch<AnalyticsData>(`/classes/${classId}/analytics`);
                setData(res);
                setTopicIndex(0);
            } catch (err) {
                setError(getErrorMessage(err));
            } finally {
                setIsLoading(false);
            }
        };
        fetchAnalytics();
    }, [classId]);

    useEffect(() => {
        const fetchAi = async () => {
            setIsAiLoading(true);
            try {
                const res = await apiFetch<{ ai_recommendation: string }>(`/classes/${classId}/analytics/recommendation`);
                if (res.ai_recommendation) setAiRecommendation(res.ai_recommendation);
            } catch (err) {
                if (data?.ai_recommendation) setAiRecommendation(data.ai_recommendation);
            } finally {
                setIsAiLoading(false);
            }
        };
        fetchAi();
    }, [classId]);

    useEffect(() => {
        if (scrollRef.current && data?.topics_avg && activeChart === 'bar') {
            const activeBar = scrollRef.current.children[0]?.children[topicIndex] as HTMLElement;
            if (activeBar) activeBar.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
        }
    }, [topicIndex, data, activeChart]);

    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        if (labelsScrollRef.current) labelsScrollRef.current.scrollLeft = e.currentTarget.scrollLeft;
    };

    const nextTopic = () => { if (data?.topics_avg) setTopicIndex((prev) => (prev + 1) % data.topics_avg.length); };
    const prevTopic = () => { if (data?.topics_avg) setTopicIndex((prev) => (prev - 1 + data.topics_avg.length) % data.topics_avg.length); };

    const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
    const item = { hidden: { opacity: 0, y: 30 }, show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } } };

    const totalGrades = data ? (data.grade_distribution.grade_5 + data.grade_distribution.grade_4 + data.grade_distribution.grade_3 + data.grade_distribution.grade_2) : 0;

    const getPieGradient = () => {
        if (!data || totalGrades === 0) return 'conic-gradient(#EAF1F1 0% 100%)';
        const p5 = (data.grade_distribution.grade_5 / totalGrades) * 100;
        const p4 = (data.grade_distribution.grade_4 / totalGrades) * 100;
        const p3 = (data.grade_distribution.grade_3 / totalGrades) * 100;
        return `conic-gradient(#94A9BE 0% ${p5}%, #B2CDE0 ${p5}% ${p5 + p4}%, #EAF1F1 ${p5 + p4}% ${p5 + p4 + p3}%, #596070 ${p5 + p4 + p3}% 100%)`;
    };

    const currentTopicName = data?.topics_avg?.[topicIndex]?.topic_title || 'НЕТ ТЕМ';

    const hasWeakTopic = data?.weakest_topic && data.weakest_topic.avg_score <= 4.0;
    const weakTopicTitle = hasWeakTopic ? data.weakest_topic?.topic_title : 'Нет';

    const metricInfo = {
        avg: {
            title: 'Средний балл',
            text: 'Это среднее арифметическое всех оценок класса по предмету. Показывает общую успеваемость. Выше 4.0 — отличный результат, ниже 3.5 — классу требуется помощь.'
        },
        debts: {
            title: 'Долги',
            text: 'Количество неотработанных задолженностей. Сюда входят пропущенные домашние задания и неудовлетворительные оценки, которые еще не исправлены.'
        },
        weak: {
            title: 'Слабая тема',
            text: hasWeakTopic 
                ? 'Тема, по которой у класса самый низкий средний балл. Рекомендуется посвятить ей следующий урок или провести дополнительное занятие.'
                : 'Отличная работа! Все темы усвоены со средним баллом выше 4.0. Слабых тем нет.'
        }
    };

    // Подготовка данных для легенды круговой диаграммы
    const gradeStats = data ? [
        { label: 'Оценка 5', value: data.grade_distribution.grade_5, color: 'bg-[#94A9BE]' },
        { label: 'Оценка 4', value: data.grade_distribution.grade_4, color: 'bg-[#B2CDE0]' },
        { label: 'Оценка 3', value: data.grade_distribution.grade_3, color: 'bg-[#EAF1F1]' },
        { label: 'Оценка 2', value: data.grade_distribution.grade_2, color: 'bg-[#596070]' },
    ] : [];

    return (
        <div className="relative min-h-screen bg-[#EAF1F1] overflow-x-hidden flex justify-center">
            <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <motion.div variants={container} initial="hidden" animate="show" className="relative z-10 w-full max-w-[440px] flex flex-col pb-10">
                <motion.header variants={item} className="bg-[#B2CDE0] px-6 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between">
                    <button onClick={() => navigate('/teacher')} className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors">
                        <img src={homeIcon} alt="Home" className="w-full h-full object-contain" />
                    </button>
                    <h1 className="text-[28px] font-extrabold text-[#596070] tracking-wide">{displayClassName}</h1>
                    <button className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors" onClick={() => navigate(`/teacher/classes/${classId}/journal`, { state: location.state })}>
                        <img src={journalIcon} alt="Journal" className="w-full h-full object-contain" />
                    </button>
                </motion.header>

                <motion.div variants={item} className="mt-6 px-5">
                    <h2 className="text-[22px] font-extrabold text-[#596070] leading-tight mb-2">
                        УСПЕВАЕМОСТЬ ПО ПРЕДМЕТУ:<br/>МАТЕМАТИКА
                    </h2>

                    <div className="relative flex items-center justify-center mb-3 min-h-[48px]">
                        <AnimatePresence mode="wait">
                            {activeChart === 'bar' && (
                                <motion.div key="slider" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ duration: 0.2 }} className="flex items-center justify-center gap-1 text-[18px] font-extrabold text-[#596070] max-w-[230px] w-full mx-auto">
                                    <button onClick={prevTopic} className="text-[#94A9BE] hover:text-[#596070] transition-colors shrink-0 cursor-pointer text-2xl px-1">&larr;</button>
                                    <span className="text-center leading-tight break-words line-clamp-2 flex-1">{currentTopicName}</span>
                                    <button onClick={nextTopic} className="text-[#94A9BE] hover:text-[#596070] transition-colors shrink-0 cursor-pointer text-2xl px-1">&rarr;</button>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <div className="absolute right-0 flex gap-1">
                            <button onClick={() => setActiveChart('bar')} className={`w-8 h-8 rounded-md flex items-center justify-center transition-all ${activeChart === 'bar' ? 'bg-[#596070] text-white shadow-md' : 'bg-[#94A9BE] text-white hover:bg-[#859bb1]'}`}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg>
                            </button>
                            <button onClick={() => setActiveChart('pie')} className={`w-8 h-8 rounded-md flex items-center justify-center transition-all ${activeChart === 'pie' ? 'bg-[#596070] text-white shadow-md' : 'bg-[#94A9BE] text-white hover:bg-[#859bb1]'}`}>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>
                            </button>
                        </div>
                    </div>

                    <p className="text-[12px] text-[#859bb1] font-bold mb-3 text-center">
                        {activeChart === 'bar'
                            ? "График показывает средний балл по темам. Чем выше столбик — тем лучше класс усвоил тему."
                            : "Круговая диаграмма показывает распределение оценок в классе. В центре — средний балл."}
                    </p>

                    <div className="bg-white/60 backdrop-blur-xl rounded-[40px] p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.05)] border border-white/50 min-h-[320px] flex flex-col justify-center overflow-hidden">
                        <AnimatePresence mode="wait">
                            {isLoading ? (
                                <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex items-center justify-center text-[#596070] font-bold">Загрузка данных...</motion.div>
                            ) : error ? (
                                <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col items-center justify-center text-[#D48B8B] font-bold text-center px-4">
                                    <p>{error}</p>
                                    <Button onClick={() => window.location.reload()} className="mt-4 bg-[#D48B8B] text-white rounded-full px-6 h-10 text-sm">Повторить</Button>
                                </motion.div>
                            ) : activeChart === 'bar' ? (
                                <motion.div key="bar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }} className="flex-1 flex flex-col w-full items-center justify-center">
                                    
                                    <div className="flex w-full h-[220px] items-center justify-center">
                                        <div className="flex flex-col justify-between text-[10px] font-bold text-[#859bb1] pr-2 h-[160px] items-end shrink-0 pb-1">
                                            <span>5.0</span><span>4.0</span><span>3.0</span><span>2.0</span><span>1.0</span>
                                        </div>
                                        
                                        <div ref={scrollRef} onScroll={handleScroll} className="flex-1 overflow-x-auto [&::-webkit-scrollbar]:hidden relative h-[200px] border-l border-b border-gray-300 snap-x snap-mandatory">
                                            <div className="absolute inset-x-0 top-0 h-[160px] flex flex-col justify-between pointer-events-none opacity-20">
                                                <div className="border-b border-gray-400 w-full h-0"></div><div className="border-b border-gray-400 w-full h-0"></div><div className="border-b border-gray-400 w-full h-0"></div><div className="border-b border-gray-400 w-full h-0"></div>
                                            </div>
                                            <div className="flex gap-2 min-w-max items-end relative z-10 px-2 h-full pb-1 mx-auto">
                                                {data?.topics_avg?.map((topic, index) => {
                                                    const heightPercent = `${Math.max((topic.avg_score / 5) * 100, 5)}%`;
                                                    const isActive = index === topicIndex;
                                                    return (
                                                        <div key={topic.topic_id} onClick={() => setTopicIndex(index)} className="flex flex-col items-center justify-end h-full w-[72px] cursor-pointer group snap-center shrink-0">
                                                            <motion.div 
                                                                initial={{ height: 0 }} 
                                                                animate={{ height: heightPercent }} 
                                                                transition={{ delay: 0.1 + index * 0.05, type: "spring", stiffness: 80 }} 
                                                                className={`w-[75%] rounded-t-md relative transition-colors flex justify-center ${isActive ? 'bg-[#596070] shadow-md' : 'bg-[#94A9BE] group-hover:bg-[#596070]'}`}
                                                            >
                                                                <span className="text-white font-extrabold text-[11px] absolute top-1.5 left-1/2 -translate-x-1/2 pointer-events-none">
                                                                    {topic.avg_score}
                                                                </span>
                                                            </motion.div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex w-full mt-2 pl-[28px]">
                                        <div ref={labelsScrollRef} className="flex-1 overflow-x-auto [&::-webkit-scrollbar]:hidden">
                                            <div className="flex gap-2 min-w-max px-2">
                                                {data?.topics_avg?.map((topic, index) => (
                                                    <div key={topic.topic_id} className="w-[72px] flex justify-center snap-center">
                                                        <span className={`text-[10px] font-bold text-center leading-[1.1] line-clamp-3 w-full ${index === topicIndex ? 'text-[#596070]' : 'text-[#859bb1]'}`}>{topic.topic_title}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ) : (
                                /* 👇 ОБНОВЛЕННЫЙ БЛОК КРУГОВОЙ ДИАГРАММЫ 👇 */
                                <motion.div key="pie" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }} className="flex-1 flex flex-col items-center justify-center w-full">
                                    <motion.div initial={{ scale: 0.8, rotate: -90 }} animate={{ scale: 1, rotate: 0 }} transition={{ type: "spring", stiffness: 100 }} className="w-40 h-40 rounded-full mb-6 relative flex items-center justify-center shadow-lg" style={{ background: getPieGradient() }}>
                                        <div className="w-24 h-24 bg-[#F4F8F8] rounded-full flex items-center justify-center shadow-inner">
                                            <span className="font-extrabold text-[#596070] text-2xl">{data?.big_numbers.avg_score?.toFixed(1) || '0.0'}</span>
                                        </div>
                                    </motion.div>
                                    
                                    {/* Новая понятная легенда с процентами */}
                                    <div className="flex flex-col gap-2 w-full max-w-[260px] mt-2">
                                        {gradeStats.map((stat, i) => {
                                            const percent = totalGrades > 0 ? Math.round((stat.value / totalGrades) * 100) : 0;
                                            return (
                                                <div key={i} className="flex items-center justify-between w-full bg-[#F4F8F8]/50 px-3 py-1.5 rounded-xl border border-white/50">
                                                    <div className="flex items-center gap-2">
                                                        <div className={`w-3 h-3 ${stat.color} rounded-sm shadow-sm`}></div>
                                                        <span className="text-[13px] font-bold text-[#596070]">{stat.label}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-[14px] font-extrabold text-[#596070]">{stat.value}</span>
                                                        <span className="text-[11px] font-bold text-[#859bb1] w-9 text-right">({percent}%)</span>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <p className="text-[12px] text-[#859bb1] font-bold mt-6 mb-2 text-center px-4">
                        Сводные показатели успеваемости класса
                    </p>
                    <div className="grid grid-cols-3 gap-3">
                        <button onClick={() => setActiveMetric('avg')} className="bg-white/60 backdrop-blur-md rounded-2xl p-3 flex flex-col items-center justify-center shadow-sm border border-white/50 hover:bg-white/80 transition-colors">
                            <span className="text-[10px] font-bold text-[#859bb1] uppercase text-center mb-1">Средний балл</span>
                            <span className="text-xl font-extrabold text-[#596070]">{data?.big_numbers.avg_score?.toFixed(1) || '-'}</span>
                        </button>
                        <button onClick={() => setActiveMetric('debts')} className="bg-white/60 backdrop-blur-md rounded-2xl p-3 flex flex-col items-center justify-center shadow-sm border border-white/50 hover:bg-white/80 transition-colors">
                            <span className="text-[10px] font-bold text-[#859bb1] uppercase text-center mb-1">Долги</span>
                            <span className="text-xl font-extrabold text-[#596070]">{data?.big_numbers.active_debts || 0}</span>
                        </button>
                        <button onClick={() => setActiveMetric('weak')} className="bg-white/60 backdrop-blur-md rounded-2xl p-3 flex flex-col items-center justify-center shadow-sm border border-white/50 hover:bg-white/80 transition-colors">
                            <span className="text-[10px] font-bold text-[#859bb1] uppercase text-center mb-1">Слабая тема</span>
                            <span className="text-[13px] font-extrabold text-[#596070] text-center line-clamp-2 leading-tight">
                                {weakTopicTitle}
                            </span>
                        </button>
                    </div>

                    <div className="bg-white/60 backdrop-blur-md rounded-[40px] p-6 mt-4 shadow-[0px_10px_30px_rgba(0,0,0,0.05)] border border-white/50 flex flex-col items-center text-center">
                        <h3 className="text-[20px] font-extrabold text-[#596070] mb-3">РЕКОМЕНДАЦИИ ИИ</h3>
                        {isAiLoading ? (
                            <div className="flex flex-col items-center justify-center h-20">
                                <div className="w-6 h-6 border-4 border-[#94A9BE] border-t-transparent rounded-full animate-spin mb-2"></div>
                                <p className="text-[12px] font-bold text-[#859bb1]">ИИ анализирует данные...</p>
                            </div>
                        ) : (
                            <p className="text-[13px] text-[#859bb1] font-bold leading-relaxed min-h-[40px]">{aiRecommendation || 'Проблем не обнаружено. Отличная работа!'}</p>
                        )}
                    </div>

                    <Button 
                        onClick={() => navigate(`/teacher/classes/${classId}/seating`)} 
                        className="w-full h-[60px] mt-6 bg-[#C9D9E6] hover:bg-[#b5c8d8] text-[#596070] rounded-[30px] text-[18px] font-extrabold transition-all shadow-sm"
                    >
                        ИЗМЕНИТЬ РАССАДКУ
                    </Button>
                </motion.div>
            </motion.div>

            <AnimatePresence>
                {activeMetric && (
                    <motion.div 
                        initial={{ opacity: 0 }} 
                        animate={{ opacity: 1 }} 
                        exit={{ opacity: 0 }} 
                        className="fixed inset-0 bg-black/40 z-[100] flex items-end justify-center"
                        onClick={() => setActiveMetric(null)}
                    >
                        <motion.div 
                            initial={{ y: "100%" }} 
                            animate={{ y: 0 }} 
                            exit={{ y: "100%" }} 
                            transition={{ type: "spring", damping: 25, stiffness: 200 }}
                            className="bg-[#F4F8F8] w-full max-w-[440px] rounded-t-[40px] p-6 pb-10 shadow-2xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="w-12 h-1.5 bg-[#C9D9E6] rounded-full mx-auto mb-5" />
                            <h3 className="text-[22px] font-extrabold text-[#596070] mb-3">
                                {metricInfo[activeMetric].title}
                            </h3>
                            <p className="text-[14px] text-[#859bb1] font-bold leading-relaxed mb-6">
                                {metricInfo[activeMetric].text}
                            </p>
                            <Button 
                                onClick={() => setActiveMetric(null)}
                                className="w-full h-[56px] bg-[#94A9BE] hover:bg-[#859bb1] text-white rounded-2xl font-extrabold text-[16px]"
                            >
                                Понятно
                            </Button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
