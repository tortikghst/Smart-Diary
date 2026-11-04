import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from './pages/Login';
import TeacherDashboard from "./pages/TeacherDashboard";
import StudentDashboard from "./pages/StudentDashboard";
import ClassPage from "./pages/ClassPage";
import SeatingPage from "./pages/SeatingPage";
import TeacherTestsPage from './pages/TeacherTestsPage';
import JournalPage from "./pages/JournalPage";
import TestCreatePage from "./pages/TestCreatePage";
import StudentMascot from "./pages/StudentMascot";
import StudentDebtsPage from "@/pages/StudentDebtsPage.tsx";
import StudentTestsPage from "@/pages/StudentTestsPage.tsx";
import StudentTestTakePage from "@/pages/StudentTestTakePage.tsx";
import StudentTestReviewPage from './pages/StudentTestReviewPage';

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Login />} />
                <Route path="/teacher" element={<TeacherDashboard />} />
                <Route path="/student" element={<StudentDashboard />} />
                <Route path="/student/mascot" element={<StudentMascot />} />
                <Route path="/student/debts" element={<StudentDebtsPage />} />
                <Route path="/student/tests" element={<StudentTestsPage />} />
                <Route path="/student/tests/:testId" element={<StudentTestTakePage />} />
                <Route path="/student/tests/:testId/review" element={<StudentTestReviewPage />} />
                <Route path="*" element={<div>Страница не найдена</div>} />
                <Route path="/teacher/classes/:classId" element={<ClassPage />} />
                <Route path="/teacher/classes/:classId/seating" element={<SeatingPage />} />
                <Route path="/teacher/classes/:classId/journal" element={<JournalPage />} />
                <Route path="/teacher/tests" element={<TeacherTestsPage />} />
                <Route path="/teacher/tests/create" element={<TestCreatePage />} />
                <Route path="/teacher/tests/edit/:testId" element={<TestCreatePage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;