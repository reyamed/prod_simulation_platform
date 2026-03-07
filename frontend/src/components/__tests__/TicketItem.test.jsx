import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { TicketItem } from '../../App.jsx';
import { describe, it, expect, vi } from 'vitest';

describe('TicketItem', () => {
    it('renders Skip Stage button when ticket is open', () => {
        const mockTicket = {
            id: 1,
            subject: 'Broken DB',
            sender_name: 'Dev',
            body: 'Fix it',
            status: 'open',
            hints: '[]'
        };
        const handleSkip = vi.fn();
        const handleValidate = vi.fn();

        render(<TicketItem ticket={mockTicket} handleSkip={handleSkip} handleValidate={handleValidate} isSkipping={false} />);

        const skipBtn = screen.getByText('Skip Stage ⏭️');
        expect(skipBtn).toBeInTheDocument();

        fireEvent.click(skipBtn);
        expect(handleSkip).toHaveBeenCalled();
    });

    it('does not render Skip Stage button when ticket is resolved', () => {
        const mockTicket = {
            id: 1,
            subject: 'Broken DB',
            sender_name: 'Dev',
            body: 'Fix it',
            status: 'resolved',
            hints: '[]'
        };

        render(<TicketItem ticket={mockTicket} handleSkip={vi.fn()} handleValidate={vi.fn()} isSkipping={false} />);

        expect(screen.queryByText('Skip Stage ⏭️')).not.toBeInTheDocument();
    });
});
