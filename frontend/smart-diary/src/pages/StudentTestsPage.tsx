import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronLeft, PlayCircle, Star } from 'lucide-react';
import { Button } from "../../@/components/ui/button";
import bgImage from '../assets/bg.png';

interface AvailableTest {
    test_id: number;
    topic_title: string;
    subject_name: string;
    attempts_used: number;
    attempts_left: number;
    best_percent: number | null;
}

interface DashboardData {
    available_tests: AvailableTest[];
}

export default function StudentTestsPage() {
    const navigate = useNavigate();
    const [tests, setTests] = useState<AvailableTest[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchTests = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) return;

            try {
                const res = await fetch('/api/v1/student/dashboard', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const data: DashboardData = await res.json();
                    setTests(data.available_tests || []);
                }
            } catch (err) {
                console.error("Ошибка загрузки тестов:", err);
            } finally {
                setIsLoading(false);
            }
        };

        fetchTests();
    }, []);

    return (
        <div className="relative min-h-screen bg-[#f2f6f9] overflow-x-hidden flex justify-center font-sans pb-10">
            <div className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <div className="relative z-10 w-full max-w-[430px] flex flex-col">
                {/* Шапка */}
                <header className="bg-[#B2CDE0] px-5 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between sticky top-0 z-20">
                    <button onClick={() => navigate('/student')} className="w-10 h-10 bg-[#94A9BE] rounded-xl flex items-center justify-center text-white hover:bg-[#859bb1] transition-colors">
                        <ChevronLeft size={24} />
                    </button>
                    <h1 className="text-[20px] font-extrabold text-[#3b506c]">Доступные тесты</h1>
                    <div className="w-10 h-10" />
                </header>

                <div className="mt-6 px-4">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-[200px] text-[#3b506c] animate-pulse font-bold">Загрузка тестов...</div>
                    ) : tests.length === 0 ? (
                        <div className="bg-white/80 backdrop-blur-md rounded-[30px] p-8 text-center shadow-sm border border-white/50 mt-10">
                            <div className="w-20 h-20 bg-[#EBF1F1] rounded-full flex items-center justify-center mx-auto mb-4 text-[#94A9BE]">
                                <PlayCircle size={40} />
                            </div>
                            <h2 className="text-[20px] font-extrabold text-[#3b506c] mb-2">Тестов пока нет</h2>
                            <p className="text-[#859bb1] text-sm font-bold">Учитель еще не назначил новые тесты. Отдыхайте!</p>
                        </div>
                    ) : (
                        <div className="flex flex-col gap-4">
                            {tests.map((test) => (
                                <motion.div
                                    key={test.test_id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="bg-white/80 backdrop-blur-md rounded-[30px] p-5 shadow-sm border border-white/50 flex flex-col"
                                >
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="flex-1 pr-2">
                                            <p className="text-[11px] font-extrabold text-[#94A9BE] uppercase tracking-wider mb-1">{test.subject_name}</p>
                                            <h3 className="text-[16px] font-extrabold text-[#3b506c] leading-tight">{test.topic_title}</h3>
                                        </div>
                                        {test.best_percent !== null && (
                                            <div className="bg-[#EBF1F1] text-[#94A9BE] px-2.5 py-1 rounded-lg flex items-center gap-1 shrink-0">
                                                <Star size={12} fill="currentColor" />
                                                <span className="text-[12px] font-bold">{test.best_percent}%</span>
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex items-center justify-between mt-2">
                                        <div className="flex flex-col">
                                            <span className="text-[11px] font-bold text-[#859bb1]">Попытки</span>
                                            <span className="text-[14px] font-extrabold text-[#3b506c]">
                                                {test.attempts_used} / {test.attempts_used + test.attempts_left}
                                            </span>
                                        </div>

                                        <Button
                                            onClick={() => navigate(`/student/tests/${test.test_id}`)}
                                            disabled={test.attempts_left === 0}
                                            className={`h-10 px-6 rounded-xl font-extrabold text-[14px] transition-all ${
                                                test.attempts_left === 0
                                                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                                    : 'bg-[#B2CDE0] hover:bg-[#94A9BE] text-[#3b506c] shadow-sm'
                                            }`}
                                        >
                                            {test.attempts_left === 0 ? 'Попытки кончились' : 'Начать тест'}
                                        </Button>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}