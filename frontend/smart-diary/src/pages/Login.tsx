import { useNavigate } from 'react-router-dom';
import {Button} from "../../@/components/ui/button.tsx";
import { motion } from "framer-motion";
import bgImage from '@/assets/bg.png';
import { useState } from "react";

export default function Login() {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async (role: 'student' | 'teacher') => {
        setIsLoading(true);
        setError('');

        const initDataValue = role === 'student' ? 'dev_student_string' : 'dev_teacher_string';

        try {
            const response = await fetch(`/api/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({initData: initDataValue}),
            });

            if (!response.ok) {
                throw new Error('Ошибка авторизации. Проверьте данные.');
            }
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            if (role === 'student') {
                navigate('/student');
            }
            else {navigate('/teacher');}
        }
        catch (err: any){
            setError(err.message || 'Не удалось подключиться к серверу.');
        }
        finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative flex items-center justify-center min-h-screen bg-[#ffffff] overflow-hidden">
            <div
                className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-70 z-0"
                style={{ backgroundImage: `url(${bgImage})` }}
            />

            <motion.div
                initial={{ opacity: 0, y: 150, scale: 0.8 }}
                animate={{
                    opacity: 1,
                    scale: 1,
                    y: [0, -10, 0]
                }}
                transition={{
                    opacity: { duration: 0.8 },
                    scale: { type: "spring", stiffness: 100, damping: 15 },
                    y: {
                        duration: 4,
                        repeat: Infinity, // Вернул бесконечность для плавного парения
                        repeatType: "reverse",
                        ease: "linear",
                        delay: 0.8
                    }
                }}
                // Добавил will-change-transform для супер-плавности на уровне видеокарты
                className="relative z-10 flex flex-col items-center justify-center w-[350px] h-[320px] bg-[#EBF1F1] rounded-[55px] shadow-[0px_10px_30px_rgba(0,0,0,0.15)] will-change-transform"
            >
                <motion.h1
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.5 }}
                    className="text-[36px] font-extrabold text-[#596070] mb-[40px]"
                >
                    Авторизация
                </motion.h1>
                {error && (
                    <p className="text-red-500 text-sm mb-2 absolute top-20">{error}</p>
                )}

                <motion.div
                    initial={{ opacity: 0, x: -50 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4, type: "spring", stiffness: 120 }}
                    className="mb-[20px]"
                >
                    <Button
                        className="w-[270px] h-[55px] bg-[#B2CDE0] hover:bg-[#a1bed3] text-[#596070] rounded-[55px] text-[20px] font-extrabold transition-all duration-200 hover:scale-105 active:scale-95 shadow-sm disabled:opacity-50"
                        onClick={() => handleLogin("student")}
                        disabled={isLoading}
                    >
                        {isLoading ? "Загрузка..." : "Войти как ученик"}
                    </Button>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, x: 50 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5, type: "spring", stiffness: 120 }}
                >
                    <Button
                        className="w-[270px] h-[55px] bg-[#94A9BE] hover:bg-[#859bb1] text-[#596070] rounded-[55px] text-[20px] font-extrabold transition-all duration-200 hover:scale-105 active:scale-95 shadow-sm disabled:opacity-50"
                        onClick={() => handleLogin("teacher")}
                        disabled={isLoading}
                    >
                        {isLoading ? "Загрузка..." : "Войти как учитель"}
                    </Button>
                </motion.div>

            </motion.div>
        </div>
    );
}