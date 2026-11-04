import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from "../../@/components/ui/button.tsx";
import bgImage from '@/assets/bg.png';
import homeIcon from '@/assets/Home-Logo.svg';
import journalIcon from '@/assets/Journal-Logo.svg';

interface TopicAvg {
    topic_id: number;
    topic_title: string;
    avg_score: number;
    mastery_percent: number;
    students_with_gaps: number;
}

interface AnalyticsData {
    class_id: number;
    big_numbers: {
        avg_score: number | null;
        active_debts: number;
    };
    grade_distribution: {
        grade_5: number;
        grade_4: number;
        grade_3: number;
        grade_2: number;
    };
    topics_avg: TopicAvg[];
    weakest_topic: TopicAvg | null;
    ai_recommendation: string | null;
}

export default function ClassPage() {
    const { classId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const scrollRef = useRef<HTMLDivElement>(null);

    const displayClassName = location.state?.className
        ? `${location.state.className} КЛАСС`
        : `${classId} КЛАСС`;

    const [data, setData] = useState<AnalyticsData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [activeChart, setActiveChart] = useState<'bar' | 'pie'>('bar');
    const [topicIndex, setTopicIndex] = useState(0);

    useEffect(() => {
        const fetchAnalytics = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) return;

            try {
                const response = await fetch(`/api/v1/classes/${classId}/analytics`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (response.ok) {
                    const result = await response.json();
                    setData(result);
                    setTopicIndex(0);
                }
            }
            catch (err) {
                console.error(err);
            }
            finally {
                setIsLoading(false);
            }
        };
        fetchAnalytics();
    }, [classId]);

    useEffect(() => {
        if (scrollRef.current && data?.topics_avg && activeChart === 'bar') {
            const activeBar = scrollRef.current.children[topicIndex] as HTMLElement;
            if (activeBar) {
                activeBar.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            }
        }
    }, [topicIndex, data, activeChart]);

    const nextTopic = () => {
        if (!data?.topics_avg || data.topics_avg.length === 0) return;
        setTopicIndex((prev) => (prev + 1) % data.topics_avg.length);
    };

    const prevTopic = () => {
        if (!data?.topics_avg || data.topics_avg.length === 0) return;
        setTopicIndex((prev) => (prev - 1 + data.topics_avg.length) % data.topics_avg.length);
    };

    const container = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    const item = {
        hidden: { opacity: 0, y: 30 },
        show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } }
    };

    const totalGrades = data ? (data.grade_distribution.grade_5 + data.grade_distribution.grade_4 + data.grade_distribution.grade_3 + data.grade_distribution.grade_2) : 0;

    const getPieGradient = () => {
        if (!data || totalGrades === 0) return 'conic-gradient(#EAF1F1 0% 100%)';
        const p5 = (data.grade_distribution.grade_5 / totalGrades) * 100;
        const p4 = (data.grade_distribution.grade_4 / totalGrades) * 100;
        const p3 = (data.grade_distribution.grade_3 / totalGrades) * 100;

        return `conic-gradient(
            #94A9BE 0% ${p5}%, 
            #B2CDE0 ${p5}% ${p5 + p4}%, 
            #EAF1F1 ${p5 + p4}% ${p5 + p4 + p3}%, 
            #596070 ${p5 + p4 + p3}% 100%
        )`;
    };

    const currentTopicName = data?.topics_avg?.[topicIndex]?.topic_title || 'НЕТ ТЕМ';

    return (
        <div className="relative min-h-screen bg-[#EAF1F1] overflow-x-hidden flex justify-center">
            <div
                className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0"
                style={{ backgroundImage: `url(${bgImage})` }}
            />

            <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="relative z-10 w-full max-w-[440px] flex flex-col pb-10"
            >
                <motion.header
                    variants={item}
                    className="bg-[#B2CDE0] px-6 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between"
                >
                    <button onClick={() => navigate('/teacher')} className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors">
                        <img src={homeIcon} alt="Home" className="w-full h-full object-contain" />
                    </button>
                    <h1 className="text-[28px] font-extrabold text-[#596070] tracking-wide">
                        {displayClassName}
                    </h1>
                    <button className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors"  onClick={() => navigate(`/teacher/classes/${classId}/journal`, { state: location.state })} >
                        <img src={journalIcon} alt="Journal" className="w-full h-full object-contain" />
                    </button>
                </motion.header>

                <motion.div variants={item} className="mt-6 px-5">
                    <h2 className="text-[22px] font-extrabold text-[#596070] leading-tight mb-4">
                        УСПЕВАЕМОСТЬ ПО ПРЕДМЕТУ:<br/>МАТЕМАТИКА
                    </h2>

                    <div className="relative flex items-center justify-center mb-6 min-h-[48px]">
                        <AnimatePresence mode="wait">
                            {activeChart === 'bar' && (
                                <motion.div
                                    key="slider"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    transition={{ duration: 0.2 }}
                                    className="flex items-center justify-center gap-1 text-[18px] font-extrabold text-[#596070] max-w-[230px] w-full mx-auto"
                                >
                                    <button onClick={prevTopic} className="text-[#94A9BE] hover:text-[#596070] transition-colors shrink-0 cursor-pointer text-2xl px-1">&larr;</button>
                                    <span className="text-center leading-tight break-words line-clamp-2 flex-1">
                                        {currentTopicName}
                                    </span>
                                    <button onClick={nextTopic} className="text-[#94A9BE] hover:text-[#596070] transition-colors shrink-0 cursor-pointer text-2xl px-1">&rarr;</button>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <div className="absolute right-0 flex gap-1">
                            <button
                                onClick={() => setActiveChart('bar')}
                                className={`w-8 h-8 rounded-md flex items-center justify-center transition-all ${activeChart === 'bar' ? 'bg-[#596070] text-white shadow-md' : 'bg-[#94A9BE] text-white hover:bg-[#859bb1]'}`}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="12" y1="20" x2="12" y2="10"></line>
                                    <line x1="18" y1="20" x2="18" y2="4"></line>
                                    <line x1="6" y1="20" x2="6" y2="16"></line>
                                </svg>
                            </button>
                            <button
                                onClick={() => setActiveChart('pie')}
                                className={`w-8 h-8 rounded-md flex items-center justify-center transition-all ${activeChart === 'pie' ? 'bg-[#596070] text-white shadow-md' : 'bg-[#94A9BE] text-white hover:bg-[#859bb1]'}`}
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
                                    <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <div className="bg-white/60 backdrop-blur-xl rounded-[40px] p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.05)] border border-white/50 min-h-[320px] flex flex-col justify-between overflow-hidden">

                        <AnimatePresence mode="wait">
                            {isLoading ? (
                                <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex items-center justify-center text-[#596070] font-bold">
                                    Загрузка данных...
                                </motion.div>
                            ) : activeChart === 'bar' ? (
                                <motion.div
                                    key="bar"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.3 }}
                                    className="flex-1 flex flex-col justify-end w-full"
                                >
                                    <div
                                        ref={scrollRef}
                                        className="flex overflow-x-auto gap-3 pb-2 snap-x snap-mandatory [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] h-[200px] items-end"
                                    >
                                        {data?.topics_avg.map((topic, index) => {
                                            const height = `${Math.max((topic.avg_score / 5) * 100, 10)}%`;
                                            const isActive = index === topicIndex;
                                            return (
                                                <div
                                                    key={topic.topic_id}
                                                    onClick={() => setTopicIndex(index)}
                                                    className="flex flex-col items-center justify-end gap-2 flex-none w-[70px] snap-center h-full cursor-pointer group relative"
                                                >
                                                    <motion.div
                                                        initial={{ height: 0 }}
                                                        animate={{ height: height }}
                                                        transition={{ delay: 0.1 + index * 0.05, type: "spring", stiffness: 80 }}
                                                        className={`w-full rounded-t-md relative transition-colors ${isActive ? 'bg-[#596070] shadow-md' : 'bg-[#94A9BE] group-hover:bg-[#596070]'}`}
                                                    >
                                                        <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[#596070] text-white text-[10px] py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10 pointer-events-none">
                                                            Балл: {topic.avg_score} | Пробелы: {topic.students_with_gaps}
                                                        </div>
                                                    </motion.div>

                                                    {/* ОБНОВЛЕННЫЙ БЛОК ТЕКСТА */}
                                                    <div className="h-11 w-full flex items-start justify-center pt-1 overflow-hidden">
                                                        <span className={`text-[10px] font-bold text-center leading-[1.1] line-clamp-3 w-full break-words hyphens-auto ${isActive ? 'text-[#596070]' : 'text-[#859bb1]'}`}>
                                                            {topic.topic_title}
                                                        </span>
                                                    </div>

                                                </div>
                                            );
                                        })}
                                    </div>
                                </motion.div>
                            ) : (
                                <motion.div
                                    key="pie"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    transition={{ duration: 0.3 }}
                                    className="flex-1 flex flex-col items-center justify-center"
                                >
                                    <motion.div
                                        initial={{ scale: 0.8, rotate: -90 }}
                                        animate={{ scale: 1, rotate: 0 }}
                                        transition={{ type: "spring", stiffness: 100 }}
                                        className="w-40 h-40 rounded-full mb-6 relative flex items-center justify-center shadow-lg"
                                        style={{ background: getPieGradient() }}
                                    >
                                        <div className="w-24 h-24 bg-[#F4F8F8] rounded-full flex items-center justify-center shadow-inner">
                                            <span className="font-extrabold text-[#596070] text-2xl">
                                                {data?.big_numbers.avg_score?.toFixed(1) || '0.0'}
                                            </span>
                                        </div>
                                    </motion.div>
                                    <div className="grid grid-cols-2 gap-x-8 gap-y-2 w-full max-w-[250px]">
                                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#94A9BE] rounded-sm"></div><span className="text-[13px] font-bold text-[#596070]">Оценка 5: {data?.grade_distribution.grade_5}</span></div>
                                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#B2CDE0] rounded-sm"></div><span className="text-[13px] font-bold text-[#596070]">Оценка 4: {data?.grade_distribution.grade_4}</span></div>
                                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#EAF1F1] rounded-sm"></div><span className="text-[13px] font-bold text-[#596070]">Оценка 3: {data?.grade_distribution.grade_3}</span></div>
                                        <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#596070] rounded-sm"></div><span className="text-[13px] font-bold text-[#596070]">Оценка 2: {data?.grade_distribution.grade_2}</span></div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <div className="grid grid-cols-3 gap-3 mt-4">
                        <div className="bg-white/60 backdrop-blur-md rounded-2xl p-3 flex flex-col items-center justify-center shadow-sm border border-white/50">
                            <span className="text-[10px] font-bold text-[#859bb1] uppercase text-center mb-1">Средний балл</span>
                            <span className="text-xl font-extrabold text-[#596070]">{data?.big_numbers.avg_score?.toFixed(1) || '-'}</span>
                        </div>
                        <div className="bg-white/60 backdrop-blur-md rounded-2xl p-3 flex flex-col items-center justify-center shadow-sm border border-white/50">
                            <span className="text-[10px] font-bold text-[#859bb1] uppercase text-center mb-1">Долги</span>
                            <span className="text-xl font-extrabold text-[#596070]">{data?.big_numbers.active_debts || 0}</span>
                        </div>
                        <div className="bg-white/60 backdrop-blur-md rounded-2xl p-3 flex flex-col items-center justify-center shadow-sm border border-white/50">
                            <span className="text-[10px] font-bold text-[#859bb1] uppercase text-center mb-1">Слабая тема</span>
                            <span className="text-[13px] font-extrabold text-[#596070] text-center line-clamp-2 leading-tight">
                                {data?.weakest_topic?.topic_title || 'Нет'}
                            </span>
                        </div>
                    </div>

                    <div className="bg-white/60 backdrop-blur-md rounded-[40px] p-6 mt-4 shadow-[0px_10px_30px_rgba(0,0,0,0.05)] border border-white/50 flex flex-col items-center text-center">
                        <h3 className="text-[20px] font-extrabold text-[#596070] mb-3">
                            РЕКОМЕНДАЦИИ ИИ
                        </h3>
                        <p className="text-[13px] text-[#859bb1] font-bold leading-relaxed mb-6">
                            {isLoading ? "Анализируем..." : data?.ai_recommendation || 'Проблем не обнаружено. Отличная работа!'}
                        </p>
                        <Button
                            onClick={() => navigate(`/teacher/classes/${classId}/seating`)}
                            className="w-full h-[60px] bg-[#C9D9E6] hover:bg-[#b5c8d8] text-[#596070] rounded-[30px] text-[18px] font-extrabold transition-all"
                        >
                            ИЗМЕНИТЬ РАССАДКУ
                        </Button>
                    </div>
                </motion.div>
            </motion.div>
        </div>
    );
}