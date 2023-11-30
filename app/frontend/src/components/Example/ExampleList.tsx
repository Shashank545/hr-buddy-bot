import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "What should I do to take personal time off?",
        value: "What should I do to take personal time off?"
    },
    {
        text: "How can I check how many days of time off I have left?", 
        value: "How can I check how many days of time off I have left?"
    },
    {
        text: "Is there any benefit I can receive for getting married?", 
        value: "Is there any benefit I can receive for getting married?"
    }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
