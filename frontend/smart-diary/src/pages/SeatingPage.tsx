import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { DndContext, useDraggable, useDroppable, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import type { DragEndEvent } from '@dnd-kit/core';
import { Button } from "../../@/components/ui/button.tsx";
import bgImage from '@/assets/bg.png';
import homeIcon from '@/assets/Home-Logo.svg';
import journalIcon from '@/assets/Journal-Logo.svg';

interface Seat {
    row: number;
    col: number;
    student_id: number;
    markers: string[];
}

interface Layout {
    grid: { rows: number; cols: number };
    seats: Seat[];
    teacher: { row: number; col: number };
}

interface SeatingData {
    class_id: number;
    layout_json: Layout;
    teacher_position: string;
    photo_url: string | null;
}

interface Student {
    student_id: number;
    full_name: string;
}

const AVAILABLE_MARKERS = [
    { id: 'vision', label: 'Плохое зрение', icon: '👁️' },
    { id: 'hearing', label: 'Плохой слух', icon: '👂' },
    { id: 'behavior', label: 'Нарушает дисциплину', icon: '⚡' }
];

const SeatItem = ({ seat, student, onClick }: { seat: Seat, student: Student | null, onClick: () => void }) => {
    const isDraggable = !!student;

    const { attributes, listeners, setNodeRef: setDragRef, transform, isDragging } = useDraggable({
        id: `seat-${seat.row}-${seat.col}`,
        data: { seat },
        disabled: !isDraggable
    });

    const { setNodeRef: setDropRef, isOver } = useDroppable({
        id: `seat-${seat.row}-${seat.col}`
    });

    const setRefs = (node: HTMLElement | null) => {
        setDragRef(node);
        setDropRef(node);
    };

    const style = transform ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        zIndex: 50,
        opacity: isDragging ? 0.5 : 1
    } : undefined;

    if (!student) {
        return (
            <div
                ref={setDropRef}
                className={`w-full h-12 rounded-[16px] bg-[#C9D9E6]/40 transition-all duration-200 ${
                    isOver ? 'ring-2 ring-[#4A5568] scale-105 bg-[#C9D9E6]/80' : ''
                }`}
            />
        );
    }

    const parts = student.full_name.trim().split(/\s+/);
    const lastName = parts[0] || '';
    const firstName = parts[1] ? `${parts[1].charAt(0)}.` : '';
    const middleName = parts[2] ? `${parts[2].charAt(0)}.` : '';
    const shortFirstName = `${firstName}${middleName}`;

    return (
        <div
            ref={setRefs}
            style={style}
            {...listeners}
            {...attributes}
            onClick={onClick}
            title={student.full_name}
            className={`w-full h-12 rounded-[16px] flex flex-col justify-center items-center text-white shadow-sm transition-all touch-none cursor-grab active:cursor-grabbing bg-[#4A5568] relative px-1 ${
                isOver ? 'ring-2 ring-[#94A9BE] scale-105' : ''
            }`}
        >
            <span className="text-[10px] font-bold leading-[1.1] w-full text-center truncate">
                {lastName}
            </span>
            {shortFirstName && (
                <span className="text-[9px] font-medium leading-[1.1] w-full text-center truncate opacity-90">
                    {shortFirstName}
                </span>
            )}

            {seat.markers && seat.markers.length > 0 && (
                <div className="absolute -top-1.5 -right-1.5 flex gap-0.5 bg-white/90 backdrop-blur-sm px-1 py-0.5 rounded-full shadow-md border border-gray-100 z-10">
                    {seat.markers.map(m => (
                        <span key={m} className="text-[10px] leading-none">
                            {AVAILABLE_MARKERS.find(am => am.id === m)?.icon}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

export default function SeatingPage() {
    const { classId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();

    const [displayClassName, setDisplayClassName] = useState<string>(
        location.state?.className ? `${location.state.className} КЛАСС` : 'Загрузка...'
    );

    const [data, setData] = useState<SeatingData | null>(null);
    const [students, setStudents] = useState<Student[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [activeSeat, setActiveSeat] = useState<Seat | null>(null);

    const [isGridSettingsOpen, setIsGridSettingsOpen] = useState(false);
    const [tempRows, setTempRows] = useState(5);
    const [tempDesks, setTempDesks] = useState(3);

    const [toast, setToast] = useState<{ message: string, type: 'success' | 'error' } | null>(null);

    const showToast = (message: string, type: 'success' | 'error') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 3000);
    };

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
    );

    const fetchSeating = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        const headers = { 'Authorization': `Bearer ${token}` };

        try {
            if (!location.state?.className) {
                const classesRes = await fetch(`/api/v1/teacher/classes`, { headers });
                if (classesRes.ok) {
                    const classesData = await classesRes.json();
                    const currentClass = classesData.find((c: any) => c.class_id === Number(classId));
                    if (currentClass) setDisplayClassName(`${currentClass.class_name} КЛАСС`);
                    else setDisplayClassName(`${classId} КЛАСС`);
                }
            }

            const seatingRes = await fetch(`/api/v1/seating/${classId}`, { headers });
            if (seatingRes.ok) {
                const seatingData = await seatingRes.json();
                setData(seatingData);
                setTempRows(seatingData.layout_json.grid?.rows || 5);
                setTempDesks(Math.ceil((seatingData.layout_json.grid?.cols || 6) / 2));
            }

            const studentsRes = await fetch(`/api/v1/classes/${classId}/students`, { headers });
            if (studentsRes.ok) {
                const studentsData = await studentsRes.json();
                setStudents(studentsData);
            }
        } catch (err) {
            console.error("Ошибка при загрузке данных:", err);
            setDisplayClassName(`${classId} КЛАСС`);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchSeating();
    }, [classId]);

    const handleGenerate = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        setIsGenerating(true);
        console.error(null);

        try {
            const savedMarkers: Record<number, string[]> = {};
            data?.layout_json.seats.forEach(s => {
                if (s.student_id !== 0 && s.markers.length > 0) {
                    savedMarkers[s.student_id] = s.markers;
                }
            });

            const colsToGenerate = data?.layout_json?.grid?.cols || 6;

            const response = await fetch(`/api/v1/seating/${classId}/generate?cols=${colsToGenerate}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
            });

            if (!response.ok) throw new Error(`Ошибка генерации: ${response.status}`);

            const newData = await response.json();

            const updatedSeats = newData.layout_json.seats.map((seat: Seat) => {
                if (seat.student_id !== 0 && savedMarkers[seat.student_id]) {
                    return { ...seat, markers: savedMarkers[seat.student_id] };
                }
                return seat;
            });

            const finalData = {
                ...newData,
                layout_json: { ...newData.layout_json, seats: updatedSeats }
            };

            setData(finalData);
            setTempRows(finalData.layout_json.grid?.rows || 5);
            setTempDesks(Math.ceil((finalData.layout_json.grid?.cols || 6) / 2));

            await fetch(`/api/v1/seating/${classId}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ layout_json: finalData.layout_json })
            });

            showToast('Рассадка сгенерирована!', 'success');

        } catch (err: any) {
            console.error(err.message || "Неизвестная ошибка");
            showToast('Не удалось сгенерировать', 'error');
        } finally {
            setIsGenerating(false);
        }
    };

    const handleSave = async () => {
        if (!data) return;
        const token = localStorage.getItem('access_token');
        if (!token) return;

        setIsSaving(true);
        try {
            const response = await fetch(`/api/v1/seating/${classId}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ layout_json: data.layout_json })
            });

            if (!response.ok) throw new Error(`Ошибка ${response.status}`);

            showToast('Рассадка успешно сохранена!', 'success');
        } catch (err: any) {
            console.error(err);
            showToast('Ошибка при сохранении', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleDownload = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        try {
            const response = await fetch(`/api/v1/seating/${classId}/download`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) throw new Error('Картинка не сгенерирована');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `seating_class_${classId}.png`;
            document.body.appendChild(a);
            a.click();
            a.remove();

            showToast('Картинка скачана!', 'success');
        } catch (err: any) {
            showToast('Не удалось скачать картинку', 'error');
        }
    };

    const toggleMarker = async (markerId: string) => {
        if (!activeSeat || !data) return;

        const newMarkers = activeSeat.markers.includes(markerId)
            ? activeSeat.markers.filter(m => m !== markerId)
            : [...activeSeat.markers, markerId];

        const updatedSeats = data.layout_json.seats.map(s =>
            s.row === activeSeat.row && s.col === activeSeat.col
                ? { ...s, markers: newMarkers }
                : s
        );

        setData({ ...data, layout_json: { ...data.layout_json, seats: updatedSeats } });
        setActiveSeat({ ...activeSeat, markers: newMarkers });
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over || !data) return;

        if (active.id !== over.id) {
            const [activeRow, activeCol] = (active.id as string).replace('seat-', '').split('-').map(Number);
            const [overRow, overCol] = (over.id as string).replace('seat-', '').split('-').map(Number);

            const getStudentAt = (r: number, c: number) => {
                const found = data.layout_json.seats.find(s => s.row === r && s.col === c);
                return found ? { student_id: found.student_id, markers: found.markers } : { student_id: 0, markers: [] };
            };

            const activeData = getStudentAt(activeRow, activeCol);
            const overData = getStudentAt(overRow, overCol);

            let newSeats = [...data.layout_json.seats];

            newSeats = newSeats.filter(s => !(s.row === activeRow && s.col === activeCol));
            newSeats = newSeats.filter(s => !(s.row === overRow && s.col === overCol));

            if (overData.student_id !== 0) {
                newSeats.push({ row: activeRow, col: activeCol, ...overData });
            }

            if (activeData.student_id !== 0) {
                newSeats.push({ row: overRow, col: overCol, ...activeData });
            }

            setData({ ...data, layout_json: { ...data.layout_json, seats: newSeats } });
        }
    };

    const applyGridSettings = () => {
        if (!data) return;

        const actualCols = tempDesks * 2;
        const totalStudents = data.layout_json.seats.length;
        const requiredRows = Math.ceil(totalStudents / actualCols);

        // АВТОМАТИЧЕСКОЕ РАСШИРЕНИЕ: сетка не может быть меньше, чем нужно
        const finalRows = Math.max(tempRows, requiredRows);

        if (finalRows > tempRows) {
            showToast(`Сетка расширена до ${finalRows} рядов, чтобы все поместились`, 'success');
        } else {
            showToast('Сетка обновлена', 'success');
        }

        // Перераспределяем учеников в новую сетку (никого не теряем!)
        const studentsList = data.layout_json.seats
            .filter(s => s.student_id !== 0)
            .map(s => ({ student_id: s.student_id, markers: s.markers }));

        const newSeats: Seat[] = [];
        let index = 0;

        for (let r = 0; r < finalRows; r++) {
            for (let c = 0; c < actualCols; c++) {
                if (index < studentsList.length) {
                    newSeats.push({
                        row: r,
                        col: c,
                        ...studentsList[index]
                    });
                    index++;
                } else {
                    newSeats.push({
                        row: r,
                        col: c,
                        student_id: 0,
                        markers: []
                    });
                }
            }
        }

        setData({
            ...data,
            layout_json: {
                ...data.layout_json,
                grid: { rows: finalRows, cols: actualCols },
                seats: newSeats
            }
        });
        setIsGridSettingsOpen(false);
    };

    const container = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.1 } }
    };

    const item = {
        hidden: { opacity: 0, y: 30 },
        show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } }
    };

    const rows = data?.layout_json?.grid?.rows || 5;
    const cols = data?.layout_json?.grid?.cols || 6;

    const gridMatrix = Array(rows).fill(null).map(() => Array(cols).fill(null));
    data?.layout_json?.seats.forEach(s => {
        if (gridMatrix[s.row] && gridMatrix[s.row][s.col] !== undefined) {
            gridMatrix[s.row][s.col] = s;
        }
    });

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            if (!gridMatrix[r][c]) {
                gridMatrix[r][c] = { row: r, col: c, student_id: 0, markers: [] };
            }
        }
    }

    return (
        <div className="relative min-h-screen bg-[#F4F8F8] overflow-x-hidden flex justify-center pb-10">
            <div className="fixed inset-0 bg-cover bg-center opacity-40 z-0" style={{ backgroundImage: `url(${bgImage})` }} />

            <AnimatePresence>
                {toast && (
                    <motion.div
                        initial={{ opacity: 0, y: -50, scale: 0.9 }}
                        animate={{ opacity: 1, y: 20, scale: 1 }}
                        exit={{ opacity: 0, y: -50, scale: 0.9 }}
                        transition={{ type: "spring", stiffness: 300, damping: 25 }}
                        className={`fixed top-0 left-1/2 -translate-x-1/2 z-[100] pl-2 pr-6 py-2 rounded-full shadow-[0_10px_30px_rgba(0,0,0,0.1)] flex items-center gap-3 backdrop-blur-md border ${
                            toast.type === 'success'
                                ? 'bg-[#F4F8F8]/95 border-[#B2CDE0]'
                                : 'bg-[#F4F8F8]/95 border-[#D48B8B]'
                        }`}
                    >
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white shadow-sm ${
                            toast.type === 'success' ? 'bg-[#94A9BE]' : 'bg-[#D48B8B]'
                        }`}>
                            {toast.type === 'success' ? (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            ) : (
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="12" y1="8" x2="12" y2="12"></line>
                                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                </svg>
                            )}
                        </div>
                        <span className="font-bold text-[14px] text-[#596070] whitespace-nowrap tracking-wide">
                            {toast.message}
                        </span>
                    </motion.div>
                )}
            </AnimatePresence>

            <motion.div variants={container} initial="hidden" animate="show" className="relative z-10 w-full max-w-[440px] flex flex-col">
                <motion.header variants={item} className="bg-[#B2CDE0] px-6 py-4 rounded-b-[40px] shadow-sm flex items-center justify-between">
                    <button onClick={() => navigate('/teacher')} className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors">
                        <img src={homeIcon} alt="Home" className="w-full h-full object-contain" />
                    </button>
                    <h1 className="text-[28px] font-extrabold text-[#596070] tracking-wide">{displayClassName}</h1>
                    <button className="w-12 h-12 bg-[#94A9BE] rounded-xl flex items-center justify-center p-2 hover:bg-[#859bb1] transition-colors" onClick={() => navigate(`/teacher/classes/${classId}/journal`, { state: location.state })} >
                        <img src={journalIcon} alt="Journal" className="w-full h-full object-contain" />
                    </button>
                </motion.header>

                <motion.div variants={item} className="text-center mt-6 flex flex-col items-center">
                    <h2 className="text-[28px] font-extrabold text-[#596070] mb-2">Рассадка</h2>
                    <div className="bg-[#B2CDE0] text-[#596070] font-bold px-8 py-2 rounded-full shadow-sm text-sm">СТОЛ УЧИТЕЛЯ</div>
                </motion.div>

                {isLoading ? (
                    <div className="flex-1 flex items-center justify-center font-bold text-[#596070] mt-20">Загрузка...</div>
                ) : !data ? (
                    <motion.div variants={item} className="mt-10 px-6 text-center">
                        <div className="bg-white rounded-[40px] p-8 shadow-sm border border-gray-100">
                            <h2 className="text-[22px] font-bold text-[#596070] mb-2">У вас пока нет рассадки</h2>
                            <Button onClick={handleGenerate} disabled={isGenerating} className="w-full h-[60px] mt-4 bg-[#94A9BE] hover:bg-[#859bb1] text-white rounded-full text-[18px] font-extrabold">
                                {isGenerating ? "Генерация..." : "Сгенерировать рассадку"}
                            </Button>
                        </div>
                    </motion.div>
                ) : (
                    <motion.div variants={item} className="mt-6 px-4 flex flex-col gap-3">

                        <div className="flex justify-end px-1">
                            <button
                                onClick={() => setIsGridSettingsOpen(true)}
                                className="flex items-center gap-1.5 text-[#596070] font-bold text-sm hover:opacity-70 transition-opacity"
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="12" cy="12" r="3"></circle>
                                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                                </svg>
                                Настроить сетку
                            </button>
                        </div>

                        <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
                            <div className="flex flex-col gap-3 bg-white/40 p-4 rounded-[30px]">
                                {gridMatrix.map((rowSeats, r) => (
                                    <div key={r} className="flex justify-between gap-2">
                                        {Array(Math.ceil(cols / 2)).fill(null).map((_, cIndex) => {
                                            const seat1 = rowSeats[cIndex * 2];
                                            const seat2 = rowSeats[cIndex * 2 + 1];

                                            return (
                                                <div key={`desk-${r}-${cIndex}`} className="flex-1 grid grid-cols-2 gap-1.5 p-1.5 bg-white/70 rounded-[20px] shadow-sm">
                                                    <SeatItem
                                                        seat={seat1}
                                                        student={students.find(st => st.student_id === seat1.student_id) || null}
                                                        onClick={() => seat1.student_id !== 0 && setActiveSeat(seat1)}
                                                    />
                                                    {seat2 ? (
                                                        <SeatItem
                                                            seat={seat2}
                                                            student={students.find(st => st.student_id === seat2.student_id) || null}
                                                            onClick={() => seat2.student_id !== 0 && setActiveSeat(seat2)}
                                                        />
                                                    ) : (
                                                        <div className="w-full h-12 rounded-[16px] bg-[#C9D9E6]/40" />
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                ))}
                            </div>
                        </DndContext>

                        <div className="flex flex-col gap-3 mt-2">
                            <Button onClick={handleSave} disabled={isSaving} className="w-full h-[60px] bg-[#94A9BE] hover:bg-[#859bb1] text-white rounded-full text-[18px] font-extrabold shadow-md">
                                {isSaving ? "Сохранение..." : "Сохранить рассадку"}
                            </Button>
                            <Button onClick={handleDownload} className="w-full h-[60px] bg-[#C9D9E6] hover:bg-[#b5c8d8] text-[#596070] rounded-full text-[18px] font-extrabold shadow-sm">
                                Скачать картинку рассадки
                            </Button>
                            <Button onClick={handleGenerate} disabled={isGenerating} className="w-full h-[60px] bg-[#94A9BE] hover:bg-[#859bb1] text-white rounded-full text-[18px] font-extrabold shadow-md">
                                {isGenerating ? "Генерация..." : "Сгенерировать заново"}
                            </Button>
                        </div>
                    </motion.div>
                )}
            </motion.div>

            <AnimatePresence>
                {isGridSettingsOpen && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end justify-center"
                        onClick={() => setIsGridSettingsOpen(false)}
                    >
                        <motion.div
                            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
                            transition={{ type: "spring", damping: 25, stiffness: 300 }}
                            onClick={e => e.stopPropagation()}
                            className="bg-white rounded-t-[40px] p-8 w-full max-w-[440px] shadow-2xl pb-10"
                        >
                            <div className="w-12 h-1.5 bg-gray-300 rounded-full mx-auto mb-6" />

                            <h3 className="text-2xl font-extrabold text-[#596070] text-center mb-6">Размер сетки</h3>

                            <div className="flex flex-col gap-6 mb-8">
                                <div className="flex items-center justify-between bg-[#F4F8F8] p-4 rounded-2xl">
                                    <span className="font-bold text-[#596070]">Парты (сверху вниз)</span>
                                    <div className="flex items-center gap-4">
                                        <button onClick={() => setTempRows(Math.max(1, tempRows - 1))} className="w-10 h-10 bg-white rounded-full font-bold text-xl text-[#596070] shadow-sm">-</button>
                                        <span className="text-xl font-extrabold text-[#596070] w-6 text-center">{tempRows}</span>
                                        <button onClick={() => setTempRows(Math.min(10, tempRows + 1))} className="w-10 h-10 bg-white rounded-full font-bold text-xl text-[#596070] shadow-sm">+</button>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between bg-[#F4F8F8] p-4 rounded-2xl">
                                    <span className="font-bold text-[#596070]">Ряды (слева направо)</span>
                                    <div className="flex items-center gap-4">
                                        <button onClick={() => setTempDesks(Math.max(1, tempDesks - 1))} className="w-10 h-10 bg-white rounded-full font-bold text-xl text-[#596070] shadow-sm">-</button>
                                        <span className="text-xl font-extrabold text-[#596070] w-6 text-center">{tempDesks}</span>
                                        <button onClick={() => setTempDesks(Math.min(6, tempDesks + 1))} className="w-10 h-10 bg-white rounded-full font-bold text-xl text-[#596070] shadow-sm">+</button>
                                    </div>
                                </div>
                            </div>

                            <Button onClick={applyGridSettings} className="w-full h-[60px] bg-[#94A9BE] text-white rounded-full text-[18px] font-extrabold hover:bg-[#859bb1] transition-colors">
                                Применить
                            </Button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            <AnimatePresence>
                {activeSeat && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end justify-center"
                        onClick={() => setActiveSeat(null)}
                    >
                        <motion.div
                            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
                            transition={{ type: "spring", damping: 25, stiffness: 300 }}
                            onClick={e => e.stopPropagation()}
                            className="bg-white rounded-t-[40px] p-8 w-full max-w-[440px] shadow-2xl pb-10"
                        >
                            <div className="w-12 h-1.5 bg-gray-300 rounded-full mx-auto mb-6" />

                            <h3 className="text-2xl font-extrabold text-[#596070] text-center mb-1">Маркеры</h3>
                            <p className="text-center text-[#859bb1] text-sm mb-6 font-bold truncate">
                                {students.find(s => s.student_id === activeSeat.student_id)?.full_name}
                            </p>

                            <div className="flex flex-col gap-3 mb-8">
                                {AVAILABLE_MARKERS.map(marker => {
                                    const isActive = activeSeat.markers.includes(marker.id);
                                    return (
                                        <button
                                            key={marker.id}
                                            onClick={() => toggleMarker(marker.id)}
                                            className={`flex items-center justify-between p-4 rounded-2xl border-2 transition-all ${
                                                isActive ? 'border-[#596070] bg-[#F4F8F8]' : 'border-gray-100 bg-white'
                                            }`}
                                        >
                                            <span className="font-bold text-[#596070] flex items-center gap-3">
                                                <span className="text-2xl">{marker.icon}</span> {marker.label}
                                            </span>
                                            <div className={`w-7 h-7 rounded-full flex items-center justify-center ${
                                                isActive ? 'bg-[#596070] text-white' : 'bg-gray-200'
                                            }`}>
                                                {isActive && "✓"}
                                            </div>
                                        </button>
                                    )
                                })}
                            </div>

                            <Button onClick={() => setActiveSeat(null)} className="w-full h-[60px] bg-[#596070] text-white rounded-full text-[18px] font-extrabold hover:bg-gray-700 transition-colors">
                                Применить
                            </Button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}