import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Button } from "../../@/components/ui/button.tsx";
import bgImage from '@/assets/bg.png';
import { useNavigate } from "react-router-dom";
import { apiFetch } from '../utils/api';
import { getErrorMessage } from '../utils/Errors.ts';

interface UserProfile {
    full_name: string;
    role: string;
    subject?: {
        name: string;
    };
}

interface DashboardClass {
    class_id: number;
    class_name: string;
    avg_score: number | null;
    debts_count: number;
    is_problem: boolean;
}

interface TeacherDashboardData {
    classes: DashboardClass[];
    metrics: {
        total_open_debts: number;
        active_academic_year: number;
    };
    tests: any[];
}

export default function TeacherDashboard() {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [dashboard, setDashboard] = useState<TeacherDashboardData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [userData, dashboardData] = await Promise.all([
                    apiFetch<UserProfile>('/users/me'),
                    apiFetch<TeacherDashboardData>('/teacher/dashboard')
                ]);

                setUser(userData);
                setDashboard(dashboardData);
            } catch (err) {
                console.error("Ошибка загрузки дашборда:", getErrorMessage(err));
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, []);

    const container = {
        hidden: { opacity: 0 },
        show: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const item = {
        hidden: { opacity: 0, y: 30 },
        show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } }
    };

    const getClassColor = (index: number, isProblem: boolean) => {
        if (isProblem) return 'bg-red-300 text-red-900';
        const colors = ['bg-[#EBF1F1]', 'bg-[#B2CDE0]', 'bg-[#94A9BE]'];
        return `${colors[index % 3]} text-[#596070]`;
    };

    return (
        <div className="relative min-h-screen bg-[#ffffff] overflow-x-hidden flex justify-center">
            <div
                className="fixed inset-0 bg-cover bg-center bg-no-repeat opacity-40 z-0"
                style={{ backgroundImage: `url(${bgImage})` }}
            />

            <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="relative z-10 w-full max-w-[400px] flex flex-col gap-4 pb-10"
            >
                <motion.header
                    variants={item}
                    className="bg-[#B2CDE0] px-5 py-4 rounded-b-3xl shadow-sm min-h-[80px] flex flex-col justify-center"
                >
                    <h2 className="text-white font-bold text-[16px] leading-tight">
                        {isLoading ? "Загрузка..." : user?.full_name}
                    </h2>
                    <p className="text-white/80 text-[12px] font-medium mt-1">
                        {isLoading
                            ? "Пожалуйста, подождите"
                            : user?.subject?.name
                                ? `Учитель ${user.subject.name.toLowerCase()}`
                                : "Учитель"
                        }
                    </p>
                </motion.header>

                <motion.div variants={item} className="text-center mt-2">
                    <h1 className="text-[32px] font-extrabold text-[#596070]">Главная</h1>
                </motion.div>

                <motion.div
                    variants={item}
                    className="bg-white/80 backdrop-blur-md mx-4 p-5 rounded-[30px] shadow-[0px_4px_20px_rgba(0,0,0,0.05)] min-h-[160px]"
                >
                    <h2 className="text-center text-[20px] font-bold text-[#596070] mb-4">Классы</h2>
                    {isLoading ? (
                        <div className="text-center text-[#596070]">Загрузка...</div>
                    ) : dashboard?.classes.length === 0 ? (
                        <div className="text-center text-[#596070]">Нет классов</div>
                    ) : (
                        <div className="grid grid-cols-3 gap-3">
                            {dashboard?.classes.map((cls, index) => (
                                <motion.button
                                    onClick={() => navigate(`/teacher/classes/${cls.class_id}`, { state: { className: cls.class_name } })}
                                    key={cls.class_id}
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                    className={`h-16 rounded-2xl font-bold text-[18px] shadow-sm ${getClassColor(index, cls.is_problem)}`}
                                >
                                    {cls.class_name}
                                </motion.button>
                            ))}
                        </div>
                    )}
                </motion.div>

                <motion.div
                    variants={item}
                    className="bg-white/80 backdrop-blur-md mx-4 p-5 rounded-[30px] shadow-[0px_4px_20px_rgba(0,0,0,0.05)] min-h-[240px]"
                >
                    <h2 className="text-center text-[20px] font-bold text-[#596070] mb-2">Сводка по классам</h2>
                    <p className="text-[12px] font-bold text-[#859bb1] text-center mb-6">Средний балл (от 1 до 5)</p>

                    {isLoading ? (
                        <div className="text-center text-[#596070]">Загрузка графика...</div>
                    ) : (
                        <div className="flex flex-col w-full">
                            <div className="flex w-full">
                                {/* Ось Y */}
                                <div className="flex flex-col justify-between text-[10px] font-bold text-[#859bb1] pr-2 h-44 items-end pb-8">
                                    <span>5.0</span>
                                    <span>4.0</span>
                                    <span>3.0</span>
                                    <span>2.0</span>
                                    <span>1.0</span>
                                </div>
                                
                                {/* Сам график */}
                                <div className="flex items-end justify-around w-full h-44 border-l border-b border-gray-300 pb-1 relative">
                                    {/* Сетка (линии на фоне) */}
                                    <div className="absolute inset-0 flex flex-col justify-between pointer-events-none opacity-20 pb-8">
                                        <div className="border-b border-gray-400 w-full h-0"></div>
                                        <div className="border-b border-gray-400 w-full h-0"></div>
                                        <div className="border-b border-gray-400 w-full h-0"></div>
                                        <div className="border-b border-gray-400 w-full h-0"></div>
                                    </div>

                                    {dashboard?.classes.map((cls, index) => {
                                        const score = cls.avg_score || 0;
                                        const heightPercent = `${(score / 5) * 100}%`;
                                        const color = cls.is_problem ? 'bg-[#D48B8B]' : 'bg-[#94A9BE]';

                                        return (
                                            <div key={cls.class_id} className="relative flex flex-col items-center justify-end h-full w-10 z-10 group pb-8">
                                                
                                                {/* Столбик с цифрой ВНУТРИ */}
                                                <motion.div
                                                    initial={{ height: 0 }}
                                                    animate={{ height: heightPercent }}
                                                    transition={{ delay: 0.3 + (index * 0.1), duration: 0.6, type: "spring" }}
                                                    className={`w-full ${color} rounded-t-md shadow-sm relative flex justify-center items-start pt-1`}
                                                >
                                                    <span className="text-[11px] font-extrabold text-white drop-shadow-md">
                                                        {score > 0 ? score.toFixed(1) : ''}
                                                    </span>
                                                </motion.div>
                                                
                                                {/* Название класса снизу */}
                                                <div className="absolute bottom-0 h-8 flex items-center justify-center w-full">
                                                    <span className="text-[#596070] font-bold text-[12px]">{cls.class_name}</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    )}
                </motion.div>

                <motion.div variants={item} className="mx-4 mt-2">
                    <Button
                        className="w-full h-16 bg-white/80 backdrop-blur-md rounded-[30px] shadow-[0px_4px_20px_rgba(0,0,0,0.05)] text-[20px] font-bold text-[#596070] hover:bg-white/90 hover:scale-[1.02] active:scale-[0.98] transition-all"
                        onClick={() => navigate('/teacher/tests')}>
                        Тесты
                    </Button>
                </motion.div>

            </motion.div>
        </div>
    );
}
